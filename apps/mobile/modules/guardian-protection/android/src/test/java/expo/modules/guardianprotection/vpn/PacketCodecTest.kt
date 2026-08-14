package expo.modules.guardianprotection.vpn

import java.net.InetAddress
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
}
