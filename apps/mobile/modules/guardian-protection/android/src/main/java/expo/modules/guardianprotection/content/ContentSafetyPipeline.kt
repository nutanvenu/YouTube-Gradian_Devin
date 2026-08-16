package expo.modules.guardianprotection.content

import java.nio.charset.StandardCharsets
import java.text.Normalizer
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/** Raw fields live only for the duration of a single local classification call. */
data class ContentObservation(
  val source: SignalSource,
  val appRef: String,
  val title: CharSequence?,
  val text: CharSequence?,
  val capabilityLevel: ContentCapabilityLevel,
)

data class ContentRiskFinding(
  val category: ContentRiskCategory,
  val severity: ContentRiskSeverity,
  val confidence: Double,
  val reasonCodes: Set<ContentRiskReasonCode>,
  val classifierVersion: String = "deterministic-rules-v1",
)

/** A replaceable local provider; it has no enforcement, transport, or storage dependency. */
fun interface ContentRiskClassifier {
  fun classify(normalizedText: String, source: SignalSource): ContentRiskFinding?
}

object ContentTextNormalizer {
  const val MAX_NORMALIZED_CHARS = 1_200

  fun normalize(vararg fields: CharSequence?): String {
    val raw = fields.filterNotNull().joinToString(" ").take(MAX_NORMALIZED_CHARS * 2)
    val compatibility = Normalizer.normalize(raw, Normalizer.Form.NFKC)
    val bounded = StringBuilder(MAX_NORMALIZED_CHARS)
    compatibility.codePoints().forEach { codePoint ->
      if (bounded.length >= MAX_NORMALIZED_CHARS) return@forEach
      val kind = Character.getType(codePoint)
      when {
        kind == Character.FORMAT.toInt() || kind == Character.CONTROL.toInt() -> Unit
        Character.isWhitespace(codePoint) -> bounded.append(' ')
        else -> bounded.appendCodePoint(codePoint)
      }
    }
    return bounded.toString().replace(Regex("\\s+"), " ").trim().lowercase()
  }
}

/** The deterministic MVP classifier is deliberately not presented as an ML model. */
class DeterministicContentRiskClassifier : ContentRiskClassifier {
  override fun classify(normalizedText: String, source: SignalSource): ContentRiskFinding? {
    if (normalizedText.isBlank() || isEducationalOrNegated(normalizedText)) return null

    val selfHarmDirect = SELF_HARM_DIRECT.containsMatchIn(normalizedText)
    val selfHarmIntent = SELF_HARM_INTENT.containsMatchIn(normalizedText)
    if (selfHarmDirect && selfHarmIntent) {
      return finding(
        ContentRiskCategory.SELF_HARM_SUICIDE,
        ContentRiskSeverity.CRITICAL,
        0.94,
        setOf(ContentRiskReasonCode.SELF_HARM_DIRECT, ContentRiskReasonCode.SELF_HARM_INTENT),
      )
    }
    if (selfHarmDirect) {
      return finding(
        ContentRiskCategory.SELF_HARM_SUICIDE,
        ContentRiskSeverity.HIGH,
        0.81,
        setOf(ContentRiskReasonCode.SELF_HARM_DIRECT),
      )
    }
    if (ADULT_NUDITY.containsMatchIn(normalizedText)) {
      return finding(
        ContentRiskCategory.ADULT_NUDITY,
        ContentRiskSeverity.HIGH,
        0.82,
        setOf(ContentRiskReasonCode.ADULT_NUDITY),
      )
    }
    if (WEAPONS_INSTRUCTION.containsMatchIn(normalizedText)) {
      return finding(
        ContentRiskCategory.WEAPONS,
        ContentRiskSeverity.HIGH,
        0.79,
        setOf(ContentRiskReasonCode.WEAPONS_INSTRUCTION),
      )
    }
    if (DANGEROUS_CHALLENGE.containsMatchIn(normalizedText)) {
      return finding(
        ContentRiskCategory.DANGEROUS_CHALLENGE,
        ContentRiskSeverity.MEDIUM,
        0.72,
        setOf(ContentRiskReasonCode.DANGEROUS_CHALLENGE),
      )
    }
    return null
  }

  private fun finding(
    category: ContentRiskCategory,
    severity: ContentRiskSeverity,
    confidence: Double,
    reasonCodes: Set<ContentRiskReasonCode>,
  ) = ContentRiskFinding(category, severity, confidence, reasonCodes)

  private fun isEducationalOrNegated(value: String): Boolean =
    EDUCATIONAL_CONTEXT.containsMatchIn(value) || NEGATED_SAFETY_CONTEXT.containsMatchIn(value)

  private companion object {
    val SELF_HARM_DIRECT = Regex("\\b(?:suicide|kill myself|end my life|self[ -]?harm|hurt myself)\\b")
    val SELF_HARM_INTENT = Regex("\\b(?:plan|tonight|going to|want to|can't go on|no reason to live)\\b")
    val ADULT_NUDITY = Regex("\\b(?:porn|nudes?|explicit sexual)\\b")
    val WEAPONS_INSTRUCTION = Regex("\\b(?:how to|tutorial|instructions?)\\b.{0,40}\\b(?:make|build)\\b.{0,30}\\b(?:bomb|gun|weapon)\\b")
    val DANGEROUS_CHALLENGE = Regex("\\b(?:choking challenge|blackout challenge|fire challenge)\\b")
    val EDUCATIONAL_CONTEXT = Regex(
      "\\b(?:news|headline|lesson|homework|school|teacher|documentary|history|museum|exhibit|medical|doctor|prevention|resources|journalism|book|novel|lyrics|song)\\b",
    )
    val NEGATED_SAFETY_CONTEXT = Regex(
      "\\b(?:do not|don't|never|not)\\b.{0,24}\\b(?:hurt yourself|self[ -]?harm|kill yourself|suicide)\\b",
    )
  }
}

/** This value has no title, body, URL query, node tree, or screenshot field by design. */
data class MinimizedContentRiskEvent(
  val source: SignalSource,
  val appRef: String,
  val fingerprint: String,
  val category: ContentRiskCategory,
  val severity: ContentRiskSeverity,
  val confidence: Double,
  val reasonCode: String,
  val classifierVersion: String,
  val capabilityLevel: ContentCapabilityLevel,
  val action: ContentAction,
  val occurredAtMillis: Long = System.currentTimeMillis(),
) {
  fun toPersistedMap(): Map<String, Any> = mapOf(
    "signal_source" to source.name,
    "app_ref" to appRef,
    "fingerprint" to fingerprint,
    "category" to category.name,
    "severity" to severity.name,
    "confidence" to confidence,
    "reason_code" to reasonCode,
    "classifier_version" to classifierVersion,
    "capability_level" to capabilityLevel.name,
    "action" to action.name,
    "occurred_at_millis" to occurredAtMillis,
  )
}

class ContentSafetyPipeline(
  private val classifier: ContentRiskClassifier,
) {
  fun inspect(
    observation: ContentObservation,
    blockThreshold: ContentRiskSeverity,
    fingerprintKey: ByteArray,
  ): MinimizedContentRiskEvent? {
    if (!APP_REF.matches(observation.appRef) || fingerprintKey.size < 16) return null
    var normalized = ContentTextNormalizer.normalize(observation.title, observation.text)
    return try {
      val finding = classifier.classify(normalized, observation.source) ?: return null
      val action = when {
        finding.severity.rank >= blockThreshold.rank -> ContentAction.BLOCK_AND_REQUEST
        finding.severity.rank >= ContentRiskSeverity.MEDIUM.rank -> ContentAction.WARN
        else -> ContentAction.ALLOW
      }
      MinimizedContentRiskEvent(
        source = observation.source,
        appRef = observation.appRef,
        fingerprint = keyedFingerprint(fingerprintKey, observation.source, observation.appRef, normalized),
        category = finding.category,
        severity = finding.severity,
        confidence = finding.confidence,
        reasonCode = finding.reasonCodes.map { it.name }.sorted().joinToString("+"),
        classifierVersion = finding.classifierVersion,
        capabilityLevel = observation.capabilityLevel,
        action = action,
      )
    } finally {
      // The normalized copy is short-lived and is never returned, stored, logged, or bridged.
      normalized = ""
    }
  }

  private fun keyedFingerprint(
    key: ByteArray,
    source: SignalSource,
    appRef: String,
    normalized: String,
  ): String {
    val mac = Mac.getInstance("HmacSHA256")
    mac.init(SecretKeySpec(key, "HmacSHA256"))
    mac.update(source.name.toByteArray(StandardCharsets.UTF_8))
    mac.update(0)
    mac.update(appRef.toByteArray(StandardCharsets.UTF_8))
    mac.update(0)
    return mac.doFinal(normalized.toByteArray(StandardCharsets.UTF_8)).joinToString("") {
      "%02x".format(it.toInt() and 0xff)
    }
  }

  private val ContentRiskSeverity.rank: Int
    get() = when (this) {
      ContentRiskSeverity.LOW -> 0
      ContentRiskSeverity.MEDIUM -> 1
      ContentRiskSeverity.HIGH -> 2
      ContentRiskSeverity.CRITICAL -> 3
    }

  private companion object {
    val APP_REF = Regex("^[A-Za-z0-9._-]{1,200}$")
  }
}

object NotificationContentFilter {
  fun shouldInspect(
    packageName: String,
    isSystemNoise: Boolean,
    notificationCategory: String?,
    channelId: String?,
    title: CharSequence?,
    text: CharSequence?,
  ): Boolean {
    if (packageName.isBlank() || isSystemNoise) return false
    val metadata = listOfNotNull(notificationCategory, channelId).joinToString(" ").lowercase()
    if (metadata.contains("transport") || metadata.contains("media") || metadata.contains("playback")) return false
    val content = ContentTextNormalizer.normalize(title, text)
    if (content.isBlank() || OTP_OR_AUTH.containsMatchIn(content)) return false
    if (FINANCIAL_SENSITIVE.containsMatchIn(content)) return false
    return true
  }

  private val OTP_OR_AUTH = Regex("\\b(?:otp|one[ -]?time|verification|security|login|passcode)\\b.{0,32}\\b\\d{4,8}\\b")
  private val FINANCIAL_SENSITIVE = Regex("\\b(?:bank|credit card|debit card|account number|routing number|balance|transaction|payment)\\b")
}

data class ContentSafetyPolicy(
  val notificationEnabled: Boolean,
  val accessibilitySignalsEnabled: Boolean,
  val blockThreshold: ContentRiskSeverity,
)

/** Pure runtime seam. A service can recreate it from persisted policy after JS exits. */
class ContentSafetyRuntime(
  private val policy: () -> ContentSafetyPolicy?,
  private val fingerprintKey: ByteArray,
  private val eventSink: (MinimizedContentRiskEvent) -> Unit,
  classifier: ContentRiskClassifier,
) {
  private val pipeline = ContentSafetyPipeline(classifier)

  fun allowsAccessibilitySignals(): Boolean = policy()?.accessibilitySignalsEnabled == true

  fun processNotification(
    packageName: String,
    isSystemApp: Boolean,
    notificationCategory: String?,
    channelId: String?,
    title: CharSequence?,
    text: CharSequence?,
  ): MinimizedContentRiskEvent? {
    val current = policy() ?: return null
    if (!current.notificationEnabled || !NotificationContentFilter.shouldInspect(
        packageName, isSystemApp, notificationCategory, channelId, title, text,
      )) return null
    return inspect(
      ContentObservation(
        source = SignalSource.NOTIFICATION,
        appRef = packageName,
        title = title,
        text = text,
        capabilityLevel = ContentCapabilityLevel.BEST_EFFORT,
      ),
      current,
    )
  }

  fun processAccessibility(
    packageName: String,
    text: CharSequence,
  ): MinimizedContentRiskEvent? {
    val current = policy() ?: return null
    if (!current.accessibilitySignalsEnabled) return null
    return inspect(
      ContentObservation(
        source = SignalSource.ACCESSIBILITY_TEXT,
        appRef = packageName,
        title = null,
        text = text,
        capabilityLevel = ContentCapabilityLevel.BEST_EFFORT,
      ),
      current,
    )
  }

  private fun inspect(
    observation: ContentObservation,
    current: ContentSafetyPolicy,
  ): MinimizedContentRiskEvent? = pipeline.inspect(
    observation,
    current.blockThreshold,
    fingerprintKey,
  )?.also(eventSink)
}

object AccessibilityContentGate {
  fun shouldInspect(
    hasAffirmativeConsent: Boolean,
    signedPolicyAllowsAccessibilitySignals: Boolean,
    eventType: Int,
  ): Boolean =
    hasAffirmativeConsent && signedPolicyAllowsAccessibilitySignals && eventType in setOf(
      android.view.accessibility.AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED,
      android.view.accessibility.AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED,
    )
}
