package expo.modules.guardianprotection.vpn

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import expo.modules.guardianprotection.policy.GuardianPolicyRuntime
import java.io.FileInputStream
import java.io.FileOutputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.util.concurrent.atomic.AtomicBoolean

class GuardianVpnService : VpnService() {
  private var interfaceFd: ParcelFileDescriptor? = null
  private var worker: Thread? = null
  private val running = AtomicBoolean(false)

  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    if (running.compareAndSet(false, true)) {
      runningState = true
      startForeground(NOTIFICATION_ID, notification())
      interfaceFd = Builder()
        .setSession("Guardian protection")
        .setMtu(1500)
        .addAddress("10.0.0.2", 32)
        .addRoute("10.0.0.1", 32)
        .addDnsServer("10.0.0.1")
        .establish()
      worker = Thread(::runPacketLoop, "guardian-vpn")
      worker?.start()
    }
    return START_STICKY
  }

  override fun onDestroy() {
    running.set(false)
    runningState = false
    worker?.interrupt()
    interfaceFd?.close()
    interfaceFd = null
    super.onDestroy()
  }

  private fun runPacketLoop() {
    val fd = interfaceFd ?: return
    val input = FileInputStream(fd.fileDescriptor)
    val output = FileOutputStream(fd.fileDescriptor)
    val packet = ByteArray(32767)
    try {
      while (running.get()) {
        val length = input.read(packet)
        if (length <= 0) continue
        val query = DnsPacket.parse(packet, length) ?: continue
        val decision = GuardianPolicyRuntime.evaluateDomain(query.domain)
        if (decision.blocked) {
          GuardianPolicyRuntime.reportBlocked(query.domain, decision.reasonCode)
          output.write(query.nxdomainResponse())
        } else {
          val response = query.forward(this)
          if (response != null) output.write(response)
        }
      }
    } catch (_: Exception) {
      if (running.get()) GuardianPolicyRuntime.reportFailure("VPN_PACKET_LOOP_FAILED")
    } finally {
      input.close()
      output.close()
    }
  }

  private fun notification(): Notification {
    val channelId = "guardian-protection"
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
      getSystemService(NotificationManager::class.java).createNotificationChannel(
        NotificationChannel(channelId, "Guardian protection", NotificationManager.IMPORTANCE_LOW),
      )
    }
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
      Notification.Builder(this, channelId)
        .setSmallIcon(android.R.drawable.ic_lock_lock)
        .setContentTitle("Guardian protection active")
        .setContentText("Web protection is running")
        .setOngoing(true)
        .build()
    } else {
      @Suppress("DEPRECATION")
      Notification.Builder(this)
        .setSmallIcon(android.R.drawable.ic_lock_lock)
        .setContentTitle("Guardian protection active")
        .setContentText("Web protection is running")
        .setOngoing(true)
        .build()
    }
  }

  private class DnsPacket private constructor(
    private val original: ByteArray,
    private val ipHeaderLength: Int,
    private val udpOffset: Int,
    val domain: String,
  ) {
    fun nxdomainResponse(): ByteArray {
      val response = original.copyOf()
      val dnsOffset = udpOffset + 8
      response[dnsOffset + 2] = (response[dnsOffset + 2].toInt() or 0x80).toByte()
      response[dnsOffset + 3] = (response[dnsOffset + 3].toInt() or 0x83).toByte()
      response[dnsOffset + 6] = 0
      response[dnsOffset + 7] = 0
      response[dnsOffset + 8] = 0
      response[dnsOffset + 9] = 0
      response[dnsOffset + 10] = 0
      response[dnsOffset + 11] = 0
      return swapIpv4Endpoints(response, ipHeaderLength, udpOffset)
    }

    fun forward(service: VpnService): ByteArray? {
      val dnsPayload = original.copyOfRange(udpOffset + 8, original.size)
      return runCatching {
        DatagramSocket().use { socket ->
          service.protect(socket)
          socket.soTimeout = 2000
          socket.send(DatagramPacket(dnsPayload, dnsPayload.size, InetAddress.getByName("1.1.1.1"), 53))
          val received = ByteArray(4096)
          val response = DatagramPacket(received, received.size)
          socket.receive(response)
          val payload = response.data.copyOf(response.length)
          swapIpv4Endpoints(original, ipHeaderLength, udpOffset, payload)
        }
      }.getOrNull()
    }

    companion object {
      fun parse(packet: ByteArray, length: Int): DnsPacket? {
        if (length < 28 || packet[0].toInt() ushr 4 != 4 || packet[9].toInt() and 0xff != 17) return null
        val headerLength = (packet[0].toInt() and 0x0f) * 4
        if (length < headerLength + 8) return null
        val udpOffset = headerLength
        val destinationPort = ((packet[udpOffset + 2].toInt() and 0xff) shl 8) or
          (packet[udpOffset + 3].toInt() and 0xff)
        if (destinationPort != 53) return null
        val dnsOffset = udpOffset + 8
        if (length < dnsOffset + 13) return null
        var cursor = dnsOffset + 12
        val labels = mutableListOf<String>()
        while (cursor < length) {
          val labelLength = packet[cursor++].toInt() and 0xff
          if (labelLength == 0) break
          if (labelLength > 63 || cursor + labelLength > length) return null
          labels += packet.copyOfRange(cursor, cursor + labelLength).toString(Charsets.US_ASCII)
          cursor += labelLength
        }
        if (labels.isEmpty()) return null
        return DnsPacket(packet.copyOf(length), headerLength, udpOffset, labels.joinToString(".").lowercase())
      }

      private fun swapIpv4Endpoints(
        source: ByteArray,
        ipHeaderLength: Int,
        udpOffset: Int,
        payload: ByteArray? = null,
      ): ByteArray {
        val dnsPayload = payload ?: source.copyOfRange(udpOffset + 8, source.size)
        val packet = ByteArray(ipHeaderLength + 8 + dnsPayload.size)
        source.copyInto(packet, 0, 0, ipHeaderLength)
        source.copyInto(packet, 12, 16, 20)
        source.copyInto(packet, 16, 12, 16)
        packet[2] = ((packet.size ushr 8) and 0xff).toByte()
        packet[3] = (packet.size and 0xff).toByte()
        packet[ipHeaderLength] = source[udpOffset + 2]
        packet[ipHeaderLength + 1] = source[udpOffset + 3]
        packet[ipHeaderLength + 2] = source[udpOffset]
        packet[ipHeaderLength + 3] = source[udpOffset + 1]
        packet[ipHeaderLength + 4] = (((dnsPayload.size + 8) ushr 8) and 0xff).toByte()
        packet[ipHeaderLength + 5] = ((dnsPayload.size + 8) and 0xff).toByte()
        dnsPayload.copyInto(packet, ipHeaderLength + 8)
        packet[10] = 0
        packet[11] = 0
        val ipChecksum = checksum(packet, 0, ipHeaderLength)
        packet[10] = (ipChecksum ushr 8).toByte()
        packet[11] = ipChecksum.toByte()
        packet[ipHeaderLength + 6] = 0
        packet[ipHeaderLength + 7] = 0
        val udpChecksum = udpChecksum(packet, ipHeaderLength, dnsPayload.size + 8)
        packet[ipHeaderLength + 6] = (udpChecksum ushr 8).toByte()
        packet[ipHeaderLength + 7] = udpChecksum.toByte()
        return packet
      }

      private fun checksum(packet: ByteArray, offset: Int, length: Int): Int {
        var sum = 0L
        var index = offset
        while (index < offset + length) {
          sum += ((packet[index].toInt() and 0xff) shl 8) or
            (if (index + 1 < offset + length) packet[index + 1].toInt() and 0xff else 0)
          index += 2
        }
        while (sum ushr 16 != 0L) sum = (sum and 0xffff) + (sum ushr 16)
        return sum.inv().toInt() and 0xffff
      }

      private fun udpChecksum(packet: ByteArray, udpOffset: Int, udpLength: Int): Int {
        var sum = 0L
        for (index in 12 until 20 step 2) {
          sum += ((packet[index].toInt() and 0xff) shl 8) or (packet[index + 1].toInt() and 0xff)
        }
        sum += 17
        sum += udpLength
        var index = udpOffset
        while (index < udpOffset + udpLength) {
          sum += ((packet[index].toInt() and 0xff) shl 8) or
            (if (index + 1 < udpOffset + udpLength) packet[index + 1].toInt() and 0xff else 0)
          index += 2
        }
        while (sum ushr 16 != 0L) sum = (sum and 0xffff) + (sum ushr 16)
        return sum.inv().toInt() and 0xffff
      }
    }
  }

  companion object {
    private const val NOTIFICATION_ID = 2101
    @Volatile private var runningState = false

    fun isRunning(): Boolean = runningState

    fun start(context: Context) {
      val intent = Intent(context, GuardianVpnService::class.java)
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent)
      else context.startService(intent)
    }
  }
}
