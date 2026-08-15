package expo.modules.guardianprotection.policy

import java.net.IDN

class DomainRuleTrie(rules: List<Map<String, Any?>>) {
  private data class Entry(val domain: String, val rule: Map<String, Any?>, val order: Int)
  private val entries = rules.mapIndexedNotNull { index, rule ->
    val domain = normalize(rule["domain"] as? String ?: return@mapIndexedNotNull null)
    val match = rule["match"] as? String ?: "EXACT"
    if (domain.isEmpty() || isPublicSuffix(domain)) {
      null
    } else {
      Entry(if (match == "SUBDOMAINS") "*.$domain" else domain, rule, index)
    }
  }

  fun match(value: String): Map<String, Any?>? {
    val candidate = normalize(value)
    if (candidate.isEmpty()) return null
    return entries
      .filter { entry ->
        entry.domain == candidate ||
          (entry.domain.startsWith("*.") && (candidate == entry.domain.drop(2) || candidate.endsWith(".${entry.domain.drop(2)}")))
      }
      .maxWithOrNull(compareBy<Entry> { it.domain.length }.thenBy { it.order })
      ?.rule
  }

  private fun normalize(value: String): String = runCatching {
    val host = value.substringAfter("://", value).substringBefore('/').substringBefore(':').trimEnd('.')
    IDN.toASCII(host, IDN.USE_STD3_ASCII_RULES).lowercase()
  }.getOrDefault("")

  private fun isPublicSuffix(domain: String): Boolean =
    domain in setOf("com", "org", "net", "co.uk", "org.uk", "com.au")
}
