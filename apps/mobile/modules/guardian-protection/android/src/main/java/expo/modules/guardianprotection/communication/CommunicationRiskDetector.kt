package expo.modules.guardianprotection.communication

data class CommunicationRiskSignal(
  val category: String,
  val severity: String,
  val reasonCode: String,
)

/**
 * Deterministic rules only. Notification text is consumed by [classify] and
 * never included in the returned signal or persisted by the listener.
 */
object CommunicationRiskDetector {
  private data class Rule(
    val category: String,
    val severity: String,
    val reasonCode: String,
    val pattern: Regex,
  )

  private val rules = listOf(
    Rule("SELF_HARM", "HIGH", "RULE_SELF_HARM_TERM", Regex("\\b(?:suicide|kill myself|self[- ]harm)\\b", RegexOption.IGNORE_CASE)),
    Rule("SEXUAL_CONTENT", "HIGH", "RULE_SEXUAL_TERM", Regex("\\b(?:nudes?|explicit|sexual assault)\\b", RegexOption.IGNORE_CASE)),
    Rule("HARASSMENT", "MEDIUM", "RULE_HARASSMENT_TERM", Regex("\\b(?:threaten|stalk|dox(?:x|xing)?)\\b", RegexOption.IGNORE_CASE)),
  )

  fun classify(title: String?, text: String?): CommunicationRiskSignal? {
    val content = listOfNotNull(title, text).joinToString(" ")
    return rules.firstOrNull { it.pattern.containsMatchIn(content) }?.let {
      CommunicationRiskSignal(it.category, it.severity, it.reasonCode)
    }
  }
}
