package expo.modules.guardianprotection.vpn

import java.net.InetAddress
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DnsCacheTest {
  @Test
  fun recordsIpv4AndIpv6AnswersWithTtl() {
    val cache = DnsCache(8)
    val now = 1_000L
    val response = dnsResponse(
      "example.org",
      listOf(
        Answer(1, 60, byteArrayOf(93.toByte(), 184.toByte(), 216.toByte(), 34)),
        Answer(28, 120, InetAddress.getByName("2606:2800:220:1:248:1893:25c8:1946").address),
      ),
    )

    val leases = cache.record("example.org", response, now)

    assertEquals(2, leases.size)
    assertTrue(cache.domainFor(InetAddress.getByName("93.184.216.34"), now + 59_000) == "example.org")
    assertTrue(
      cache.domainFor(
        InetAddress.getByName("2606:2800:220:1:248:1893:25c8:1946"),
        now + 119_000,
      ) == "example.org",
    )
    assertEquals(null, cache.domainFor(InetAddress.getByName("93.184.216.34"), now + 60_000))
  }

  private data class Answer(val type: Int, val ttl: Int, val data: ByteArray)

  private fun dnsResponse(domain: String, answers: List<Answer>): ByteArray {
    val labels = domain.split('.').joinToString("") { "${it.length.toChar()}$it" }.toByteArray() + byteArrayOf(0)
    val question = labels + byteArrayOf(0, 1, 0, 1)
    val answerBytes = answers.flatMap { answer ->
      listOf<Byte>(0xc0.toByte(), 0x0c, (answer.type ushr 8).toByte(), answer.type.toByte(),
        0, 1, (answer.ttl ushr 24).toByte(), (answer.ttl ushr 16).toByte(),
        (answer.ttl ushr 8).toByte(), answer.ttl.toByte(),
        (answer.data.size ushr 8).toByte(), answer.data.size.toByte()) + answer.data.toList()
    }.toByteArray()
    val header = byteArrayOf(
      0, 1, 0x81.toByte(), 0x80.toByte(), 0, 1,
      0, answers.size.toByte(), 0, 0, 0, 0,
    )
    return header + question + answerBytes
  }
}
