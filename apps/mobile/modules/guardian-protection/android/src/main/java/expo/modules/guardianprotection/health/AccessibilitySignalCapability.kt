package expo.modules.guardianprotection.health

/**
 * Accessibility text inspection is an optional, three-party capability: Android
 * permission, local child-device consent, and a current signed parent policy.
 */
internal data class AccessibilitySignalCapability(
  val level: String,
  val detail: String,
)

internal object AccessibilitySignalCapabilityEvaluator {
  fun evaluate(
    permissionGranted: Boolean,
    localConsentGranted: Boolean,
    signedPolicyAllows: Boolean,
  ): AccessibilitySignalCapability = when {
    !permissionGranted -> AccessibilitySignalCapability(
      "UNAVAILABLE",
      "Requires Android Accessibility permission on this child device.",
    )
    !localConsentGranted -> AccessibilitySignalCapability(
      "UNAVAILABLE",
      "Requires separate Content Safety consent on this child device.",
    )
    !signedPolicyAllows -> AccessibilitySignalCapability(
      "UNAVAILABLE",
      "Disabled by the current signed parent policy. Ask a parent to enable Android content-safety signals.",
    )
    else -> AccessibilitySignalCapability(
      "BEST_EFFORT",
      "Active-window titles and headings only; editable/password text is excluded and discarded.",
    )
  }
}
