package expo.modules.guardianprotection.communication

data class CommunicationRiskSignal(
  val category: String,
  val severity: String,
  val confidence: Double,
  val reasonCode: String,
)

data class CommunicationNotificationContext(
  val packageName: String,
  val notificationCategory: String?,
  val channelId: String?,
  val repeatCount: Int = 1,
)

object CommunicationRiskDetector {
  private data class SignalRule(
    val code: String,
    val weight: Double,
    val pattern: Regex,
  )

  private data class CategoryRule(
    val category: String,
    val baseSeverity: String,
    val threshold: Double,
    val signals: List<SignalRule>,
  )

  private val rules = listOf(
    CategoryRule(
      "SELF_HARM",
      "HIGH",
      0.8,
      listOf(
        SignalRule("SELF_HARM_DIRECT", 0.6, Regex("\\b(?:suicide|kill myself|end my life|self[- ]harm)\\b", RegexOption.IGNORE_CASE)),
        SignalRule("SELF_HARM_INTENT", 0.25, Regex("\\b(?:want to|going to|plan to|can't go on|no reason to live|tonight)\\b", RegexOption.IGNORE_CASE)),
      ),
    ),
    CategoryRule(
      "SEXUAL_CONTENT",
      "HIGH",
      0.8,
      listOf(
        SignalRule("SEXUAL_EXPLICIT", 0.45, Regex("\\b(?:nudes?|explicit|porn|sexual assault|sexual content)\\b", RegexOption.IGNORE_CASE)),
        SignalRule("SEXUAL_CONTEXT", 0.4, Regex("\\b(?:assault|abuse|material|content)\\b", RegexOption.IGNORE_CASE)),
        SignalRule("SEXUAL_SOLICITATION", 0.4, Regex("\\b(?:send|share|show|trade|forward)\\b.{0,35}\\b(?:nude|photo|picture|pic)s?\\b", RegexOption.IGNORE_CASE)),
      ),
    ),
    CategoryRule(
      "SEXUAL_SOLICITATION",
      "HIGH",
      0.75,
      listOf(
        SignalRule("SOLICITATION_REQUEST", 0.35, Regex("\\b(?:send|share|show|trade|forward)\\b", RegexOption.IGNORE_CASE)),
        SignalRule("SOLICITATION_IMAGE", 0.3, Regex("\\b(?:nude|photo|picture|pic)s?\\b", RegexOption.IGNORE_CASE)),
        SignalRule("SOLICITATION_ADULT", 0.4, Regex("\\b(?:nude|intimate|explicit|sexual)\\b", RegexOption.IGNORE_CASE)),
      ),
    ),
    CategoryRule(
      "GROOMING",
      "HIGH",
      0.8,
      listOf(
        SignalRule("GROOMING_SECRET", 0.45, Regex("\\b(?:don't tell|keep this secret|keep this between us|just between us|hide this)\\b", RegexOption.IGNORE_CASE)),
        SignalRule("GROOMING_MINOR", 0.4, Regex("\\b(?:how old|your age|underage|young|meet me alone)\\b", RegexOption.IGNORE_CASE)),
      ),
    ),
    CategoryRule(
      "HARASSMENT",
      "MEDIUM",
      0.75,
      listOf(
        SignalRule("HARASSMENT_THREAT", 0.45, Regex("\\b(?:kill you|hurt(?:s)? you|get hurt|threaten(?:ed|ing)?|stalk(?:ed|ing)?)\\b", RegexOption.IGNORE_CASE)),
        SignalRule("HARASSMENT_TARGET", 0.3, Regex("\\b(?:you|your|dox(?:x|xing)?)\\b", RegexOption.IGNORE_CASE)),
        SignalRule("HARASSMENT_REPEATED", 0.2, Regex(".*")),
      ),
    ),
    CategoryRule(
      "PHISHING_CREDENTIAL_THEFT",
      "HIGH",
      0.7,
      listOf(
        SignalRule("PHISHING_CREDENTIAL", 0.4, Regex("\\b(?:password|passcode|verification code|one[- ]time code|login|bank)\\b", RegexOption.IGNORE_CASE)),
        SignalRule("PHISHING_URGENCY", 0.3, Regex("\\b(?:urgent|immediately|suspended|verify now|action required)\\b", RegexOption.IGNORE_CASE)),
        SignalRule("PHISHING_ACTION", 0.25, Regex("\\b(?:click|tap|send me|confirm|http|www\\.)\\b", RegexOption.IGNORE_CASE)),
      ),
    ),
  )

  fun classify(
    title: String?,
    text: String?,
    context: CommunicationNotificationContext,
  ): CommunicationRiskSignal? {
    val content = listOfNotNull(title, text).joinToString(" ")
    if (
      Regex(
        "\\b(?:news|headline|homework|lyrics|song|doctor|medical|lesson|history|script|act|game|character|actor|novel|book|poem|museum|exhibit|court|journalism|recipe|science|reproduction|plants|teacher|quiz|employees)\\b",
        RegexOption.IGNORE_CASE,
      ).containsMatchIn(content)
    ) {
      return null
    }
    val channelSignal = listOfNotNull(context.notificationCategory, context.channelId)
      .joinToString(" ")
      .contains(Regex("msg|chat|conversation|direct", RegexOption.IGNORE_CASE))
    val candidates = rules.mapNotNull { rule ->
      if (
        rule.category == "PHISHING_CREDENTIAL_THEFT" &&
        Regex("\\b(?:never|don't|do not|not)\\b.{0,35}\\b(?:password|passcode|code|login|bank)\\b", RegexOption.IGNORE_CASE)
          .containsMatchIn(content)
      ) {
        return@mapNotNull null
      }
      val matched = rule.signals.filter { signal ->
        signal.code != "HARASSMENT_REPEATED" && signal.pattern.containsMatchIn(content) ||
          signal.code == "HARASSMENT_REPEATED" && context.repeatCount > 1
      }
      val score = (matched.sumOf { it.weight } + if (channelSignal) 0.05 else 0.0).coerceAtMost(0.99)
      if (matched.size >= 2 && score >= rule.threshold) {
        CommunicationRiskSignal(
          category = rule.category,
          severity = if (rule.category == "SELF_HARM" && score >= 0.9) "CRITICAL" else rule.baseSeverity,
          confidence = score,
          reasonCode = matched.joinToString("+") { it.code },
        )
      } else {
        null
      }
    }
    val explicitContent = Regex("\\b(?:explicit|porn|sexual assault)\\b", RegexOption.IGNORE_CASE).containsMatchIn(content)
    return if (explicitContent) {
      candidates.firstOrNull { it.category == "SEXUAL_CONTENT" } ?: candidates.maxByOrNull { it.confidence }
    } else {
      candidates.maxByOrNull { it.confidence }
    }
  }

  fun classify(title: String?, text: String?): CommunicationRiskSignal? {
    return classify(
      title,
      text,
      CommunicationNotificationContext("com.google.android.apps.messaging", "msg", "messages"),
    )
  }

  fun isCommunicationPackage(packageName: String): Boolean {
    return packageName in setOf(
      "com.google.android.apps.messaging",
      "com.android.mms",
      "com.facebook.orca",
      "com.whatsapp",
      "com.instagram.android",
      "org.telegram.messenger",
      "com.discord",
      "com.snapchat.android",
    )
  }
}
