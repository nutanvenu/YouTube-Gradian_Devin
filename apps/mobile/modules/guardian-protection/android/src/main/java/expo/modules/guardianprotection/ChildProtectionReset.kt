package expo.modules.guardianprotection

/**
 * Explicit reset boundary between two paired children. Keeping this sequence
 * dependency-free makes the global enforcement teardown regression-testable.
 */
internal class ChildProtectionReset(
  private val stopVpn: () -> Unit,
  private val clearPendingVpnEnable: () -> Unit,
  private val clearAccessibilityEnforcement: () -> Unit,
  private val dismissContentBlock: () -> Unit,
  private val clearContentPresentation: () -> Unit,
  private val clearPolicyRuntime: () -> Unit,
  private val clearContentRuntime: () -> Unit,
  private val clearPersistedPolicy: () -> Unit,
  private val revokeContentConsent: () -> Unit,
) {
  fun reset() {
    stopVpn()
    clearPendingVpnEnable()
    clearAccessibilityEnforcement()
    dismissContentBlock()
    clearContentPresentation()
    clearPolicyRuntime()
    clearContentRuntime()
    clearPersistedPolicy()
    revokeContentConsent()
  }
}
