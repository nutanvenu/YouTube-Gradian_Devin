package expo.modules.guardianprotection.vpn

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import expo.modules.guardianprotection.BuildConfig
import expo.modules.guardianprotection.flow.AndroidFlowAttribution
import expo.modules.guardianprotection.policy.GuardianPolicyRuntime
import expo.modules.guardianprotection.policy.PolicyManager
import expo.modules.guardianprotection.storage.EncryptedPolicyStore
import java.io.FileInputStream
import java.io.FileOutputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CopyOnWriteArraySet
import java.util.concurrent.ThreadLocalRandom
import java.util.concurrent.atomic.AtomicBoolean

class GuardianVpnService : VpnService() {
  private var interfaceFd: ParcelFileDescriptor? = null
  private var worker: Thread? = null
  private var networkCallback: ConnectivityManager.NetworkCallback? = null
  private val running = AtomicBoolean(false)
  private val flows = ConcurrentHashMap<FlowKey, Flow>()
  private val dnsCache = DnsCache()
  private val attribution by lazy { AndroidFlowAttribution(this) }
  private val outputLock = Any()
  private val failureReasons = CopyOnWriteArraySet<String>()
  private var output: FileOutputStream? = null

  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    if (running.compareAndSet(false, true)) {
      startForeground(NOTIFICATION_ID, notification())
      if (VpnService.prepare(this) != null) {
        GuardianVpnPreferences.setEnabled(this, false)
        fail("VPN_CONSENT_REVOKED")
        stopSelf()
        return START_NOT_STICKY
      }
      ensurePolicyRuntime()
      registerNetworkCallback()
      interfaceFd = Builder()
        .setSession("Guardian protection")
        .setMtu(1500)
        .addAddress("10.0.0.2", 32)
        .addAddress("fd00:0:0:0:0:0:0:2", 128)
        .addRoute("0.0.0.0", 0)
        .addRoute("::", 0)
        .addDnsServer("10.0.0.1")
        .establish()
      if (interfaceFd == null) {
        GuardianVpnPreferences.setEnabled(this, false)
        fail("VPN_ESTABLISH_FAILED")
        stopSelf()
        return START_NOT_STICKY
      }
      GuardianVpnPreferences.setEnabled(this, true)
      runningState = true
      worker = Thread(::runPacketLoop, "guardian-vpn")
      worker?.start()
    }
    return START_STICKY
  }

  override fun onRevoke() {
    GuardianVpnPreferences.setEnabled(this, false)
    fail("VPN_REVOKED")
    stopSelf()
    super.onRevoke()
  }

  override fun onDestroy() {
    running.set(false)
    runningState = false
    networkCallback?.let {
      getSystemService(ConnectivityManager::class.java).unregisterNetworkCallback(it)
    }
    networkCallback = null
    flows.values.forEach { it.close() }
    flows.clear()
    worker?.interrupt()
    interfaceFd?.close()
    interfaceFd = null
    output = null
    super.onDestroy()
  }

  private fun runPacketLoop() {
    val fd = interfaceFd ?: return
    val input = FileInputStream(fd.fileDescriptor)
    output = FileOutputStream(fd.fileDescriptor)
    val packet = ByteArray(32767)
    try {
      while (running.get()) {
        val length = input.read(packet)
        if (length <= 0) continue
        val ip = PacketCodec.parseIp(packet, length) ?: continue
        when (ip.protocol) {
          UDP -> handleUdp(ip)
          TCP -> handleTcp(ip)
          else -> failOnce("UNSUPPORTED_IP_PROTOCOL_${ip.protocol}")
        }
      }
    } catch (_: Exception) {
      if (running.get()) fail("VPN_PACKET_LOOP_FAILED")
    } finally {
      input.close()
      output?.close()
      output = null
    }
  }

  private fun handleUdp(ip: IpPacket) {
    val datagram = PacketCodec.parseUdp(ip.payload) ?: return
    val key = FlowKey(ip, datagram.sourcePort, datagram.destinationPort)
    val responsibleApp = attribution.packageNamesForFlow(key.attributionKey()).firstOrNull()
    if (datagram.destinationPort == DNS_PORT) {
      handleDns(ip, datagram)
      return
    }
    val domain = dnsCache.domainFor(ip.destination)
    if (datagram.destinationPort == QUIC_PORT && domain == null && GuardianPolicyRuntime.hasActiveSnapshot()) {
      failOnce("QUIC_DOMAIN_UNRESOLVED")
      return
    }
    if (domain != null) {
      val decision = GuardianPolicyRuntime.evaluateDomain(domain, ip.destination.hostAddress)
      if (decision.blocked) {
        reportBlocked(domain, decision, responsibleApp)
        return
      }
    }
    val currentFlow = flows[key] as? UdpFlow
    if (currentFlow != null) {
      currentFlow.send(datagram.payload)
      return
    }
    if (flows.size >= MAX_FLOWS) {
      failOnce("FLOW_LIMIT_REACHED")
      return
    }
    val candidate = UdpFlow(key, ip)
    val claimedFlow = flows.putIfAbsent(key, candidate)
    if (claimedFlow == null) {
      candidate.start()
      candidate.send(datagram.payload)
    } else {
      (claimedFlow as? UdpFlow)?.send(datagram.payload)
    }
  }

  private fun handleDns(ip: IpPacket, datagram: UdpDatagram) {
    val query = DnsMessage.parse(datagram.payload) ?: return
    val responsibleApp = attribution.packageNamesForFlow(
      FlowKey(ip, datagram.sourcePort, datagram.destinationPort).attributionKey(),
    ).firstOrNull()
    val decision = GuardianPolicyRuntime.evaluateDomain(query.domain, ip.destination.hostAddress)
    if (decision.blocked) {
      reportBlocked(query.domain, decision, responsibleApp)
      write(PacketCodec.buildUdp(ip, ip.destination, ip.source, datagram.destinationPort, datagram.sourcePort, query.blockedResponse()))
      return
    }
    val upstream = if (ip.isIpv6) InetAddress.getByName("2606:4700:4700::1111")
    else InetAddress.getByName("1.1.1.1")
    runCatching {
      DatagramSocket().use { socket ->
        protect(socket)
        socket.soTimeout = DNS_TIMEOUT_MS
        socket.send(DatagramPacket(datagram.payload, datagram.payload.size, upstream, DNS_PORT))
        val received = ByteArray(4096)
        val response = DatagramPacket(received, received.size)
        socket.receive(response)
        val payload = response.data.copyOf(response.length)
        dnsCache.record(query.domain, payload)
        write(PacketCodec.buildUdp(ip, ip.destination, ip.source, datagram.destinationPort, datagram.sourcePort, payload))
      }
    }.onFailure { fail("DNS_UPSTREAM_UNAVAILABLE") }
  }

  private fun handleTcp(ip: IpPacket) {
    val segment = PacketCodec.parseTcp(ip.payload) ?: return
    val key = FlowKey(ip, segment.sourcePort, segment.destinationPort)
    val responsibleApp = attribution.packageNamesForFlow(key.attributionKey()).firstOrNull()
    val existing = flows[key] as? TcpFlow
    if (existing != null) {
      existing.accept(segment)
      return
    }
    val domain = dnsCache.domainFor(ip.destination)
    if (domain != null) {
      val decision = GuardianPolicyRuntime.evaluateDomain(domain, ip.destination.hostAddress)
      if (decision.blocked) {
        reportBlocked(domain, decision, responsibleApp)
        write(PacketCodec.buildTcp(ip, ip.destination, ip.source, segment.destinationPort, segment.sourcePort, 0, segment.sequence + 1, RST or ACK, 0))
        return
      }
    }
    if (!segment.syn || segment.ack) return
    if (flows.size >= MAX_FLOWS) {
      failOnce("FLOW_LIMIT_REACHED")
      write(PacketCodec.buildTcp(ip, ip.destination, ip.source, segment.destinationPort, segment.sourcePort, 0, segment.sequence + 1, RST or ACK, 0))
      return
    }
    val flow = TcpFlow(key, ip, segment)
    val claimedFlow = flows.putIfAbsent(key, flow)
    if (claimedFlow == null) {
      flow.start()
    } else {
      flow.close()
    }
  }

  private fun write(packet: ByteArray) {
    synchronized(outputLock) {
      runCatching { output?.write(packet) }.onFailure { fail("VPN_OUTPUT_FAILED") }
    }
  }

  private fun reportBlocked(domain: String, decision: GuardianPolicyRuntime.DomainDecision, appRef: String?) {
    GuardianPolicyRuntime.reportBlocked(domain, decision.reasonCode, decision.category, appRef)
  }

  private fun fail(reason: String) {
    GuardianPolicyRuntime.reportFailure(reason)
  }

  private fun failOnce(reason: String) {
    if (failureReasons.add(reason)) fail(reason)
  }

  private fun ensurePolicyRuntime() {
    if (GuardianPolicyRuntime.hasActiveSnapshot()) return
    val manager = PolicyManager(
      EncryptedPolicyStore(this),
      BuildConfig.GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS,
    )
    manager.start()
    GuardianPolicyRuntime.install(manager)
    if (!GuardianPolicyRuntime.hasActiveSnapshot()) failOnce("POLICY_UNAVAILABLE")
  }

  private fun registerNetworkCallback() {
    val manager = getSystemService(ConnectivityManager::class.java)
    val callback = object : ConnectivityManager.NetworkCallback() {
      override fun onLost(network: Network) {
        if (manager.activeNetwork == null) failOnce("NETWORK_UNAVAILABLE")
      }

      override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) {
        if (!capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)) {
          failOnce("CAPTIVE_PORTAL_OR_UNVALIDATED_NETWORK")
        }
      }
    }
    networkCallback = callback
    manager.registerDefaultNetworkCallback(callback)
    val active = manager.activeNetwork
    val capabilities = active?.let { manager.getNetworkCapabilities(it) }
    if (capabilities == null) failOnce("NETWORK_UNAVAILABLE")
    else if (!capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)) {
      failOnce("CAPTIVE_PORTAL_OR_UNVALIDATED_NETWORK")
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

  private abstract inner class Flow(
    protected val key: FlowKey,
    protected val request: IpPacket,
  ) {
    abstract fun close()
  }

  private inner class UdpFlow(
    key: FlowKey,
    request: IpPacket,
  ) : Flow(key, request) {
    private val socket = DatagramSocket()
    private val closed = AtomicBoolean(false)

    fun start() {
      protect(socket)
      Thread({
        val buffer = ByteArray(65535)
        while (!closed.get()) {
          runCatching {
            val packet = DatagramPacket(buffer, buffer.size)
            socket.receive(packet)
            write(PacketCodec.buildUdp(request, request.destination, request.source, key.destinationPort, key.sourcePort, packet.data.copyOf(packet.length)))
          }.onFailure {
            if (!closed.get()) fail("UDP_FORWARD_FAILED")
            return@Thread
          }
        }
      }, "guardian-udp-${key.sourcePort}").start()
    }

    fun send(payload: ByteArray) {
      runCatching {
        socket.send(DatagramPacket(payload, payload.size, request.destination, key.destinationPort))
      }.onFailure { fail("UDP_FORWARD_FAILED") }
    }

    override fun close() {
      closed.set(true)
      socket.close()
    }
  }

  private inner class TcpFlow(
    key: FlowKey,
    request: IpPacket,
    private val syn: TcpSegment,
  ) : Flow(key, request) {
    private val socket = Socket()
    private val closed = AtomicBoolean(false)
    private val localSequence = ThreadLocalRandom.current().nextLong(1, UInt.MAX_VALUE.toLong())
    private var nextClientSequence = syn.sequence + 1
    private var nextServerSequence = localSequence + 1
    private var established = false

    fun start() {
      Thread({
        runCatching {
          protect(socket)
          socket.connect(
            InetSocketAddress(request.destination, key.destinationPort),
            TCP_CONNECT_TIMEOUT_MS.toInt(),
          )
          write(PacketCodec.buildTcp(request, request.destination, request.source, key.destinationPort, key.sourcePort, localSequence, nextClientSequence, SYN or ACK, TCP_WINDOW))
          val input = socket.getInputStream()
          val buffer = ByteArray(32768)
          while (!closed.get()) {
            val count = input.read(buffer)
            if (count < 0) break
            if (count == 0) continue
            write(PacketCodec.buildTcp(request, request.destination, request.source, key.destinationPort, key.sourcePort, nextServerSequence, nextClientSequence, PSH or ACK, TCP_WINDOW, buffer.copyOf(count)))
            nextServerSequence += count
          }
          write(PacketCodec.buildTcp(request, request.destination, request.source, key.destinationPort, key.sourcePort, nextServerSequence, nextClientSequence, FIN or ACK, TCP_WINDOW))
        }.onFailure {
          write(PacketCodec.buildTcp(request, request.destination, request.source, key.destinationPort, key.sourcePort, localSequence, nextClientSequence, RST or ACK, 0))
          fail("TCP_FORWARD_FAILED")
        }.also {
          close()
        }
      }, "guardian-tcp-${key.sourcePort}").start()
    }

    fun accept(segment: TcpSegment) {
      if (segment.rst) {
        close()
        return
      }
      if (!established) {
        if (segment.ack && segment.acknowledgement == nextServerSequence) {
          established = true
          write(PacketCodec.buildTcp(request, request.destination, request.source, key.destinationPort, key.sourcePort, nextServerSequence, nextClientSequence, ACK, TCP_WINDOW))
        }
        return
      }
      if (segment.sequence != nextClientSequence) {
        write(PacketCodec.buildTcp(request, request.destination, request.source, key.destinationPort, key.sourcePort, nextServerSequence, nextClientSequence, ACK, TCP_WINDOW))
        return
      }
      if (segment.payload.isNotEmpty()) {
        runCatching {
          socket.getOutputStream().write(segment.payload)
          socket.getOutputStream().flush()
          nextClientSequence += segment.payload.size
        }.onFailure { fail("TCP_WRITE_FAILED") }
      }
      if (segment.fin) {
        nextClientSequence++
        close()
      }
      write(PacketCodec.buildTcp(request, request.destination, request.source, key.destinationPort, key.sourcePort, nextServerSequence, nextClientSequence, ACK, TCP_WINDOW))
    }

    override fun close() {
      if (closed.compareAndSet(false, true)) {
        socket.close()
        flows.remove(key)
      }
    }
  }

  private class FlowKey(
    ip: IpPacket,
    val sourcePort: Int,
    val destinationPort: Int,
  ) {
    private val source = ip.source.hostAddress
    private val destination = ip.destination.hostAddress
    private val protocol = ip.protocol

    override fun equals(other: Any?): Boolean =
      other is FlowKey && source == other.source && destination == other.destination &&
        protocol == other.protocol && sourcePort == other.sourcePort && destinationPort == other.destinationPort

    override fun hashCode(): Int = arrayOf(source, destination, protocol, sourcePort, destinationPort).contentHashCode()

    fun attributionKey(): String = "$protocol|$source:$sourcePort|$destination:$destinationPort|$sourcePort|$destinationPort"
  }

  private class DnsCache {
    private data class CachedDomain(val domain: String, val expiresAtMillis: Long)

    private val namesByAddress = ConcurrentHashMap<String, CachedDomain>()

    fun record(domain: String, response: ByteArray) {
      if (response.size < 12) return
      var offset = skipName(response, 12) + 4
      val answers = ((response[6].toInt() and 0xff) shl 8) or (response[7].toInt() and 0xff)
      repeat(answers) {
        val answer = skipName(response, offset)
        if (answer + 10 > response.size) return
        val type = ((response[answer].toInt() and 0xff) shl 8) or (response[answer + 1].toInt() and 0xff)
        val ttl = ((response[answer + 4].toLong() and 0xff) shl 24) or
          ((response[answer + 5].toLong() and 0xff) shl 16) or
          ((response[answer + 6].toLong() and 0xff) shl 8) or
          (response[answer + 7].toLong() and 0xff)
        val dataLength = ((response[answer + 8].toInt() and 0xff) shl 8) or
          (response[answer + 9].toInt() and 0xff)
        val dataOffset = answer + 10
        if (dataOffset + dataLength > response.size) return
        if ((type == 1 && dataLength == 4) || (type == 28 && dataLength == 16)) {
          runCatching {
            val address = InetAddress.getByAddress(response.copyOfRange(dataOffset, dataOffset + dataLength)).hostAddress ?: return@runCatching
            namesByAddress[address] = CachedDomain(domain, System.currentTimeMillis() + ttl * 1000)
          }
        }
        offset = dataOffset + dataLength
      }
    }

    fun domainFor(address: InetAddress): String? {
      val key = address.hostAddress ?: return null
      val cached = namesByAddress[key] ?: return null
      if (cached.expiresAtMillis <= System.currentTimeMillis()) {
        namesByAddress.remove(key, cached)
        return null
      }
      return cached.domain
    }

    private fun skipName(packet: ByteArray, start: Int): Int {
      var offset = start
      while (offset < packet.size) {
        val length = packet[offset].toInt() and 0xff
        if (length == 0) return offset + 1
        if (length and 0xc0 == 0xc0) return offset + 2
        offset += length + 1
      }
      return packet.size
    }
  }

  private class DnsMessage private constructor(
    val domain: String,
    private val original: ByteArray,
  ) {
    fun blockedResponse(): ByteArray {
      val response = original.copyOf()
      response[2] = (response[2].toInt() or 0x80).toByte()
      response[3] = (response[3].toInt() or 0x83).toByte()
      response[6] = 0
      response[7] = 0
      response[8] = 0
      response[9] = 0
      response[10] = 0
      response[11] = 0
      return response
    }

    companion object {
      fun parse(payload: ByteArray): DnsMessage? {
        if (payload.size < 17) return null
        var cursor = 12
        val labels = mutableListOf<String>()
        while (cursor < payload.size) {
          val length = payload[cursor++].toInt() and 0xff
          if (length == 0) break
          if (length > 63 || cursor + length > payload.size) return null
          labels += payload.copyOfRange(cursor, cursor + length).toString(Charsets.US_ASCII)
          cursor += length
        }
        if (labels.isEmpty()) return null
        return DnsMessage(labels.joinToString(".").lowercase(), payload)
      }
    }
  }

  companion object {
    private const val NOTIFICATION_ID = 2101
    private const val DNS_PORT = 53
    private const val QUIC_PORT = 443
    private const val UDP = 17
    private const val TCP = 6
    private const val DNS_TIMEOUT_MS = 2000
    private const val TCP_CONNECT_TIMEOUT_MS = 3000L
    private const val MAX_FLOWS = 256
    private const val TCP_WINDOW = 65535
    private const val SYN = 0x02
    private const val ACK = 0x10
    private const val PSH = 0x08
    private const val FIN = 0x01
    private const val RST = 0x04
    @Volatile private var runningState = false

    fun isRunning(): Boolean = runningState

    fun start(context: Context) {
      val intent = Intent(context, GuardianVpnService::class.java)
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent)
      else context.startService(intent)
    }

    fun stop(context: Context) {
      GuardianVpnPreferences.setEnabled(context, false)
      context.stopService(Intent(context, GuardianVpnService::class.java))
    }

    fun startWithPersistedPolicy(context: Context) {
      val store = EncryptedPolicyStore(context)
      val manager = PolicyManager(store, BuildConfig.GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS)
      manager.start()
      GuardianPolicyRuntime.install(manager)
      start(context)
    }
  }
}
