package expo.modules.guardianprotection.vpn

import java.net.InetAddress
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class PacketCodecTest {
  @Test
  fun parsesIpv4AndBuildsUdpResponseWithChecksum() {
    val source = InetAddress.getByName("10.0.0.2")
    val destination = InetAddress.getByName("1.1.1.1")
    val request = IpPacket(4, 17, source, destination, ByteArray(0), 64)
    val packet = PacketCodec.buildUdp(request, destination, source, 53, 40000, byteArrayOf(1, 2, 3))
    val parsed = PacketCodec.parseIp(packet) ?: error("IPv4 packet did not parse")
    assertEquals(4, parsed.version)
    assertEquals(destination, parsed.source)
    assertEquals(source, parsed.destination)
    val udp = PacketCodec.parseUdp(parsed.payload) ?: error("UDP packet did not parse")
    assertEquals(53, udp.sourcePort)
    assertEquals(40000, udp.destinationPort)
    assertArrayEquals(byteArrayOf(1, 2, 3), udp.payload)
  }

  @Test
  fun parsesIpv6AndBuildsTcpSegment() {
    val source = InetAddress.getByName("fd00:0:0:0:0:0:0:2")
    val destination = InetAddress.getByName("2606:4700:4700::1111")
    val request = IpPacket(6, 6, source, destination, ByteArray(0), 64)
    val packet = PacketCodec.buildTcp(request, source, destination, 40000, 443, 10, 0, 0x02, 65535)
    val parsed = PacketCodec.parseIp(packet) ?: error("IPv6 packet did not parse")
    assertEquals(6, parsed.version)
    val tcp = PacketCodec.parseTcp(parsed.payload) ?: error("TCP packet did not parse")
    assertEquals(40000, tcp.sourcePort)
    assertEquals(443, tcp.destinationPort)
    assertEquals(10, tcp.sequence)
    assertEquals(true, tcp.syn)
  }

  @Test
  fun parsesIpv6HopByHopExtensionBeforeUdp() {
    val source = InetAddress.getByName("fd00:0:0:0:0:0:0:2")
    val destination = InetAddress.getByName("2606:4700:4700::1111")
    val udp = ByteArray(11).also {
      ByteBuffer.wrap(it).order(ByteOrder.BIG_ENDIAN).apply {
        putShort(40000.toShort())
        putShort(53.toShort())
        putShort(11.toShort())
        put(1.toByte())
        put(2.toByte())
        put(3.toByte())
      }
    }
    val packet = ByteArray(40 + 8 + udp.size)
    packet[0] = 0x60
    ByteBuffer.wrap(packet).order(ByteOrder.BIG_ENDIAN).putShort(4, (8 + udp.size).toShort())
    packet[6] = 0
    packet[7] = 64
    source.address.copyInto(packet, 8)
    destination.address.copyInto(packet, 24)
    packet[40] = 17
    packet[41] = 0
    udp.copyInto(packet, 48)

    val parsed = PacketCodec.parseIp(packet) ?: error("IPv6 extension packet did not parse")
    assertEquals(17, parsed.protocol)
    assertArrayEquals(udp, parsed.payload)
  }

  @Test
  fun dropsFragmentedIpv6PacketsWithoutReassembly() {
    val packet = ByteArray(48)
    packet[0] = 0x60
    ByteBuffer.wrap(packet).order(ByteOrder.BIG_ENDIAN).putShort(4, 8)
    packet[6] = 44
    packet[7] = 64
    assertEquals(null, PacketCodec.parseIp(packet))
  }
}
