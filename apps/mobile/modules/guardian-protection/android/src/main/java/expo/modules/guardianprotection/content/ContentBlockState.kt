package expo.modules.guardianprotection.content

import java.time.Instant

/** The native block state deliberately carries only the minimized verdict tuple. */
data class ContentBlockReference(
  val appRef: String,
  val fingerprint: String,
  val category: ContentRiskCategory,
  val severity: ContentRiskSeverity,
  val confidence: Double,
  val reasonCode: String,
  val occurredAtMillis: Long,
) {
  init {
    ContentReviewEvidence(appRef, fingerprint, category, severity, confidence, reasonCode)
  }

  companion object {
    fun from(event: MinimizedContentRiskEvent) = ContentBlockReference(
      event.appRef,
      event.fingerprint,
      event.category,
      event.severity,
      event.confidence,
      event.reasonCode,
      event.occurredAtMillis,
    )
  }
}

data class ContentBlockDecision(
  val shouldBlock: Boolean,
  val reference: ContentBlockReference?,
)

/** Pure, fail-closed state transition for a single current foreground content item. */
object ContentBlockStateMachine {
  fun decide(
    event: MinimizedContentRiskEvent?,
    active: ContentBlockReference?,
    approvals: Iterable<ContentApproval>,
    deviceId: String?,
    now: Instant,
  ): ContentBlockDecision {
    if (event?.action != ContentAction.BLOCK_AND_REQUEST) {
      return ContentBlockDecision(false, null)
    }
    val candidate = ContentBlockReference.from(event)
    val approved = deviceId?.let {
      ContentReviewApprovalMatcher.matches(approvals, it, candidate.appRef, candidate.fingerprint, now)
    } == true
    if (approved) return ContentBlockDecision(false, null)
    return ContentBlockDecision(
      shouldBlock = true,
      reference = candidate,
    )
  }
}

/** Hard exclusions ensure content protection cannot trap essential Android paths. */
object ContentBlockEligibility {
  private val protectedPackages = setOf(
    "com.android.settings",
    "com.android.systemui",
    "com.android.launcher",
    "com.android.launcher3",
    "com.google.android.apps.nexuslauncher",
    "com.android.phone",
    "com.android.server.telecom",
    "com.android.emergency",
    "com.google.android.dialer",
    "com.samsung.android.dialer",
  )

  fun mayBlock(appRef: String, guardianPackage: String, isSystemOrUpdated: Boolean = false): Boolean =
    !isSystemOrUpdated && appRef.isNotBlank() && appRef != guardianPackage &&
      appRef !in protectedPackages &&
      !appRef.contains("emergency", ignoreCase = true) &&
      !appRef.contains("launcher", ignoreCase = true) &&
      !appRef.contains("settings", ignoreCase = true)
}

/** Android cannot prove a notification's content is still on screen later. */
object ContentBlockEnforcementGate {
  fun mayPersistActiveBlock(event: MinimizedContentRiskEvent?, foregroundSignal: Boolean): Boolean =
    foregroundSignal && event != null && event.source != SignalSource.NOTIFICATION &&
      event.action == ContentAction.BLOCK_AND_REQUEST
}
