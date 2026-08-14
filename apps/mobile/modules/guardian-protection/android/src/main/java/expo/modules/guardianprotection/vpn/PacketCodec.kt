package expo.modules.guardianprotection.vpn

import java.net.InetAddress
import java.nio.ByteBuffer
import java.nio.ByteOrder

internal data class IpPacket(
  val version: Int,
  val protocol: Int,
  val source: InetAddress,
  val destination: InetAddress,
  val payload: ByteArray,
  val ttl: Int,
) {
  val isIpv6: Boolean get() = version == 6
}

internal data class UdpDatagram(
  val sourcePort: Int,
  val destinationPort: Int,
  val payload: ByteArray,
)

internal data class TcpSegment(
  val sourcePort: Int,
  val destinationPort: Int,
  val sequence: Long,
  val acknowledgement: Long,
  val flags: Int,
  val window: Int,
  val payload: ByteArray,
) {
  val syn: Boolean get() = flags and 0x02 != 0
  val ack: Boolean get() = flags and 0x10 != 0
  val fin: Boolean get() = flags and 0x01 != 0
  val rst: Boolean get() = flags and 0x04 != 0
}

internal object PacketCodec {
  fun parseIp(packet: ByteArray, length: Int = packet.size): IpPacket? {
    if (length < 1) return null
    return when (packet[0].toInt() ushr 4) {
      4 -> parseIpv4(packet, length)
      6 -> parseIpv6(packet, length)
      else -> null
    }
  }

  fun parseUdp(payload: ByteArray): UdpDatagram? {
    if (payload.size < 8) return null
    val length = u16(payload, 4)
    if (length < 8 || length > payload.size) return null
    return UdpDatagram(u16(payload, 0), u16(payload, 2), payload.copyOfRange(8, length))
  }

  fun parseTcp(payload: ByteArray): TcpSegment? {
    if (payload.size < 20) return null
    val headerLength = ((payload[12].toInt() ushr 4) and 0x0f) * 4
    if (headerLength < 20 || headerLength > payload.size) return null
    return TcpSegment(
      sourcePort = u16(payload, 0),
      destinationPort = u16(payload, 2),
      sequence = u32(payload, 4),
      acknowledgement = u32(payload, 8),
      flags = u16(payload, 12) and 0x01ff,
      window = u16(payload, 14),
      payload = payload.copyOfRange(headerLength, payload.size),
    )
  }

  fun buildUdp(
    request: IpPacket,
    source: InetAddress,
    destination: InetAddress,
    sourcePort: Int,
    destinationPort: Int,
    payload: ByteArray,
  ): ByteArray {
    val udp = ByteArray(8 + payload.size)
    put16(udp, 0, sourcePort)
    put16(udp, 2, destinationPort)
    put16(udp, 4, udp.size)
    payload.copyInto(udp, 8)
    put16(udp, 6, transportChecksum(source, destination, 17, udp))
    return buildIp(request.version, 17, source, destination, udp, request.ttl)
  }

  fun buildTcp(
    request: IpPacket,
    source: InetAddress,
    destination: InetAddress,
    sourcePort: Int,
    destinationPort: Int,
    sequence: Long,
    acknowledgement: Long,
    flags: Int,
    window: Int,
    payload: ByteArray = ByteArray(0),
  ): ByteArray {
    val tcp = ByteArray(20 + payload.size)
    put16(tcp, 0, sourcePort)
    put16(tcp, 2, destinationPort)
    put32(tcp, 4, sequence)
    put32(tcp, 8, acknowledgement)
    tcp[12] = (5 shl 4).toByte()
    tcp[13] = flags.toByte()
    put16(tcp, 14, window)
    payload.copyInto(tcp, 20)
    put16(tcp, 16, transportChecksum(source, destination, 6, tcp))
    return buildIp(request.version, 6, source, destination, tcp, request.ttl)
  }

  private fun parseIpv4(packet: ByteArray, length: Int): IpPacket? {
    if (length < 20) return null
    val headerLength = (packet[0].toInt() and 0x0f) * 4
    val totalLength = u16(packet, 2)
    if (headerLength < 20 || totalLength < headerLength || totalLength > length) return null
    val protocol = packet[9].toInt() and 0xff
    val source = InetAddress.getByAddress(packet.copyOfRange(12, 16))
    val destination = InetAddress.getByAddress(packet.copyOfRange(16, 20))
    return IpPacket(4, protocol, source, destination, packet.copyOfRange(headerLength, totalLength), packet[8].toInt() and 0xff)
  }

  private fun parseIpv6(packet: ByteArray, length: Int): IpPacket? {
    if (length < 40) return null
    val payloadLength = u16(packet, 4)
    val end = 40 + payloadLength
    if (end > length) return null
    val protocol = packet[6].toInt() and 0xff
    val source = InetAddress.getByAddress(packet.copyOfRange(8, 24))
    val destination = InetAddress.getByAddress(packet.copyOfRange(24, 40))
    return IpPacket(6, protocol, source, destination, packet.copyOfRange(40, end), packet[7].toInt() and 0xff)
  }

  private fun buildIp(
    version: Int,
    protocol: Int,
    source: InetAddress,
    destination: InetAddress,
    payload: ByteArray,
    ttl: Int,
  ): ByteArray {
    val sourceBytes = source.address
    val destinationBytes = destination.address
    require(sourceBytes.size == destinationBytes.size)
    return if (version == 4) {
      val packet = ByteArray(20 + payload.size)
      packet[0] = 0x45
      packet[8] = ttl.toByte()
      packet[9] = protocol.toByte()
      put16(packet, 2, packet.size)
      sourceBytes.copyInto(packet, 12)
      destinationBytes.copyInto(packet, 16)
      payload.copyInto(packet, 20)
      put16(packet, 10, checksum(packet, 0, 20))
      packet
    } else {
      val packet = ByteArray(40 + payload.size)
      packet[0] = 0x60
      put16(packet, 4, payload.size)
      packet[6] = protocol.toByte()
      packet[7] = ttl.toByte()
      sourceBytes.copyInto(packet, 8)
      destinationBytes.copyInto(packet, 24)
      payload.copyInto(packet, 40)
      packet
    }
  }

  private fun transportChecksum(
    source: InetAddress,
    destination: InetAddress,
    protocol: Int,
    payload: ByteArray,
  ): Int {
    val sourceBytes = source.address
    val destinationBytes = destination.address
    var sum = 0L
    sum += words(sourceBytes)
    sum += words(destinationBytes)
    if (sourceBytes.size == 4) {
      sum += protocol
      sum += payload.size
    } else {
      sum += words(byteArrayOf(0, 0, 0, protocol.toByte()))
      sum += words(intToBytes(payload.size))
    }
    sum += words(payload)
    while (sum ushr 16 != 0L) sum = (sum and 0xffff) + (sum ushr 16)
    return sum.inv().toInt() and 0xffff
  }

  private fun checksum(packet: ByteArray, offset: Int, length: Int): Int {
    var sum = words(packet, offset, length)
    while (sum ushr 16 != 0L) sum = (sum and 0xffff) + (sum ushr 16)
    return sum.inv().toInt() and 0xffff
  }

  private fun words(bytes: ByteArray, offset: Int = 0, length: Int = bytes.size): Long {
    var sum = 0L
    var index = offset
    while (index < offset + length) {
      sum += ((bytes[index].toInt() and 0xff) shl 8) or
        (if (index + 1 < offset + length) bytes[index + 1].toInt() and 0xff else 0)
      index += 2
    }
    return sum
  }

  private fun intToBytes(value: Int): ByteArray =
    ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN).putInt(value).array()

  private fun u16(bytes: ByteArray, offset: Int): Int =
    ((bytes[offset].toInt() and 0xff) shl 8) or (bytes[offset + 1].toInt() and 0xff)

  private fun u32(bytes: ByteArray, offset: Int): Long =
    ((bytes[offset].toLong() and 0xff) shl 24) or
      ((bytes[offset + 1].toLong() and 0xff) shl 16) or
      ((bytes[offset + 2].toLong() and 0xff) shl 8) or
      (bytes[offset + 3].toLong() and 0xff)

  private fun put16(bytes: ByteArray, offset: Int, value: Int) {
    bytes[offset] = (value ushr 8).toByte()
    bytes[offset + 1] = value.toByte()
  }

  private fun put32(bytes: ByteArray, offset: Int, value: Long) {
    bytes[offset] = (value ushr 24).toByte()
    bytes[offset + 1] = (value ushr 16).toByte()
    bytes[offset + 2] = (value ushr 8).toByte()
    bytes[offset + 3] = value.toByte()
  }
}
