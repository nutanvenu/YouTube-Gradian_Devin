package expo.modules.guardianprotection.vpn

import java.net.InetAddress

internal class DnsCache(
  private val maxEntries: Int = 1024,
) {
  data class Lease(val address: InetAddress, val expiresAtMillis: Long)
  private data class CachedDomain(val domain: String, val expiresAtMillis: Long)
  private val namesByAddress = linkedMapOf<String, CachedDomain>()

  @Synchronized
  fun record(
    domain: String,
    response: ByteArray,
    nowMillis: Long = System.currentTimeMillis(),
  ): List<Lease> {
    if (response.size < 12) return emptyList()
    val leases = mutableListOf<Lease>()
    var offset = skipName(response, 12) + 4
    val answers = ((response[6].toInt() and 0xff) shl 8) or (response[7].toInt() and 0xff)
    repeat(answers) {
      val answer = skipName(response, offset)
      if (answer + 10 > response.size) return@repeat
      val type = ((response[answer].toInt() and 0xff) shl 8) or (response[answer + 1].toInt() and 0xff)
      val ttl = ((response[answer + 4].toLong() and 0xff) shl 24) or
        ((response[answer + 5].toLong() and 0xff) shl 16) or
        ((response[answer + 6].toLong() and 0xff) shl 8) or
        (response[answer + 7].toLong() and 0xff)
      val dataLength = ((response[answer + 8].toInt() and 0xff) shl 8) or
        (response[answer + 9].toInt() and 0xff)
      val dataOffset = answer + 10
      if (dataOffset + dataLength > response.size) return@repeat
      if ((type == 1 && dataLength == 4) || (type == 28 && dataLength == 16)) {
        runCatching {
          val address = InetAddress.getByAddress(response.copyOfRange(dataOffset, dataOffset + dataLength))
          val expiresAt = nowMillis + ttl * 1000
          val key = address.hostAddress ?: return@runCatching
          namesByAddress[key] = CachedDomain(domain, expiresAt)
          leases += Lease(address, expiresAt)
        }
      }
      offset = dataOffset + dataLength
    }
    while (namesByAddress.size > maxEntries) {
      namesByAddress.remove(namesByAddress.keys.first())
    }
    return leases
  }

  @Synchronized
  fun domainFor(address: InetAddress, nowMillis: Long = System.currentTimeMillis()): String? {
    val key = address.hostAddress ?: return null
    val cached = namesByAddress[key] ?: return null
    if (cached.expiresAtMillis <= nowMillis) {
      namesByAddress.remove(key)
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
