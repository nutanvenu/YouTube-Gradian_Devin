package expo.modules.guardianprotection.content

import java.time.Instant

private val appRefPattern = Regex("^[A-Za-z0-9._-]+$")
private val fingerprintPattern = Regex("^[a-f0-9]{64}$")
private val reasonCodePattern = Regex("^[A-Z][A-Z0-9_]*(?:\\+[A-Z][A-Z0-9_]*)*$")
private val classifierVersionPattern = Regex("^[a-z0-9][a-z0-9._-]*$")
private val publicContentIdPattern = Regex("^[A-Za-z0-9._:-]+$")
private val publicProviders = setOf("YOUTUBE", "INSTAGRAM", "X", "WEB")

/** Stable local signal sources. Values mirror packages/contracts/content-risk-contract.json. */
enum class SignalSource {
  NOTIFICATION,
  ACCESSIBILITY_TEXT,
  NETWORK_DESTINATION,
  USAGE,
  MEDIA_METADATA,
}

/** This is not a policy-engine action: it never grants broad access by itself. */
enum class ContentAction {
  ALLOW,
  WARN,
  BLOCK_AND_REQUEST,
}

enum class ContentRiskSeverity {
  LOW,
  MEDIUM,
  HIGH,
  CRITICAL,
}

enum class ContentRiskCategory {
  ADULT_NUDITY,
  SEXUAL_CONTENT,
  GROOMING_RISK,
  BULLYING_HARASSMENT,
  HATE_EXTREMISM,
  SELF_HARM_SUICIDE,
  GRAPHIC_VIOLENCE,
  VIOLENCE,
  DRUGS,
  ALCOHOL_TOBACCO,
  GAMBLING,
  WEAPONS,
  DANGEROUS_CHALLENGE,
  ANONYMOUS_CHAT,
  SCAM_FRAUD,
  MALWARE_PHISHING,
  STRONG_LANGUAGE,
  AGE_INAPPROPRIATE,
  PARENT_CUSTOM_RULE,
  UNKNOWN,
}

enum class ContentRiskReasonCode {
  ADULT_NUDITY,
  AGE_INAPPROPRIATE,
  ALCOHOL_TOBACCO_PROMOTION,
  ANONYMOUS_CHAT,
  BULLYING_TARGETED,
  CONTEXT_NEGATED,
  DANGEROUS_CHALLENGE,
  DRUG_REFERENCE,
  GAMBLING_PROMOTION,
  GRAPHIC_VIOLENCE,
  GROOMING_PATTERN,
  HATE_EXTREMISM,
  MALWARE_PHISHING,
  PARENT_CUSTOM_RULE,
  SCAM_FRAUD,
  SELF_HARM_DIRECT,
  SELF_HARM_INTENT,
  SEXUAL_CONTENT_EXPLICIT,
  STRONG_LANGUAGE,
  VIOLENCE,
  WEAPONS_INSTRUCTION,
}

enum class ContentCapabilityLevel {
  FULL,
  LIMITED,
  BEST_EFFORT,
  UNAVAILABLE,
  REGION_LIMITED,
}

private fun isCanonicalReasonCode(value: String): Boolean =
  reasonCodePattern.matches(value) && value.split("+").all { component ->
    ContentRiskReasonCode.entries.any { it.name == component }
  }

/**
 * Local-only classifier result. Extracted text deliberately has no field here,
 * so a later pipeline stage cannot accidentally persist or bridge it.
 */
data class ContentRiskVerdict(
  val category: ContentRiskCategory,
  val severity: ContentRiskSeverity,
  val confidence: Double,
  val reasonCodes: Set<String>,
  val classifierVersion: String,
  val capabilityLevel: ContentCapabilityLevel,
  val action: ContentAction,
) {
  init {
    require(confidence in 0.0..1.0)
    require(reasonCodes.isNotEmpty() && reasonCodes.size <= 8)
    require(reasonCodes.all { it.length <= 100 && isCanonicalReasonCode(it) })
    require(classifierVersion.length in 1..64 && classifierVersionPattern.matches(classifierVersion))
  }
}

data class ContentReviewEvidence(
  val appRef: String,
  val fingerprint: String,
  val category: ContentRiskCategory,
  val severity: ContentRiskSeverity,
  val confidence: Double,
  val reasonCode: String,
  val publicContentProvider: String? = null,
  val publicContentId: String? = null,
) {
  init {
    require(appRef.length in 1..200 && appRefPattern.matches(appRef))
    require(fingerprintPattern.matches(fingerprint))
    require(confidence in 0.0..1.0)
    require(reasonCode.length in 1..100 && isCanonicalReasonCode(reasonCode))
    require(
      (publicContentProvider == null && publicContentId == null) ||
        (publicContentProvider in publicProviders &&
          publicContentId != null &&
          publicContentId.length in 1..200 &&
          publicContentIdPattern.matches(publicContentId))
    )
  }
}

data class ContentApproval(
  val deviceId: String,
  val appRef: String,
  val fingerprint: String,
  val expiresAt: Instant,
) {
  init {
    require(deviceId.isNotBlank())
    require(appRef.length in 1..200 && appRefPattern.matches(appRef))
    require(fingerprintPattern.matches(fingerprint))
  }
}

object ContentRiskPolicy {
  private val defaultThresholds = mapOf(
    "YOUNG_CHILD" to ContentRiskSeverity.MEDIUM,
    "PRETEEN" to ContentRiskSeverity.MEDIUM,
    "TEEN" to ContentRiskSeverity.HIGH,
    "OLDER_TEEN" to ContentRiskSeverity.CRITICAL,
  )

  /**
   * Old signed bundles lack content_safety. Fall back by age only; do not
   * reinterpret the existing communication notification-alert threshold.
   */
  fun blockThreshold(ageBand: String, signedContentThreshold: String?): ContentRiskSeverity {
    val default = requireNotNull(defaultThresholds[ageBand]) { "Unsupported age band" }
    return signedContentThreshold?.let { raw ->
      requireNotNull(ContentRiskSeverity.entries.firstOrNull { it.name == raw }) {
        "Invalid signed content block threshold"
      }
    } ?: default
  }

  /** Parse the optional, additive signed-policy section. Legacy bundles use age defaults. */
  fun parseSignedThreshold(ageBand: String, contentSafety: Map<String, Any?>?): ContentRiskSeverity {
    if (contentSafety == null) return blockThreshold(ageBand, null)
    require(contentSafety.keys == setOf("content_block_threshold")) {
      "Invalid content_safety policy section"
    }
    val threshold = contentSafety["content_block_threshold"] as? String
      ?: throw IllegalArgumentException("Invalid signed content block threshold")
    return blockThreshold(ageBand, threshold)
  }
}

object ContentReviewApprovalMatcher {
  /**
   * An approval only has force while its exact device, app and keyed content
   * fingerprint match. Expiry is exclusive and a malformed delivery fails
   * closed. The server filters by authenticated device as a second boundary.
   */
  fun matches(
    approvals: Iterable<ContentApproval>,
    deviceId: String,
    appRef: String,
    contentFingerprint: String,
    now: Instant,
  ): Boolean = approvals.any { approval ->
    fingerprintPattern.matches(contentFingerprint) &&
      approval.deviceId == deviceId &&
      approval.appRef == appRef &&
      approval.fingerprint == contentFingerprint &&
      approval.expiresAt.isAfter(now)
  }
}
