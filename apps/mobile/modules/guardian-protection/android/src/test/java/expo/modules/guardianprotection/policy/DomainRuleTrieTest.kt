package expo.modules.guardianprotection.policy

import org.junit.Assert.assertEquals
import org.junit.Test

class DomainRuleTrieTest {
  @Test
  fun lastMatchingDuplicateRuleWins() {
    val trie = DomainRuleTrie(
      listOf(
        mapOf(
          "rule_id" to "old",
          "domain" to "example.com",
          "match" to "SUBDOMAINS",
          "action" to "BLOCK",
        ),
        mapOf(
          "rule_id" to "new",
          "domain" to "example.com",
          "match" to "SUBDOMAINS",
          "action" to "ALLOW",
        ),
      ),
    )

    assertEquals("new", trie.match("www.example.com")?.get("rule_id"))
  }
}
