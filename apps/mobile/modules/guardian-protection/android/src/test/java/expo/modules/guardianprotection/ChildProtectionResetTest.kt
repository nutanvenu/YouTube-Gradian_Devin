package expo.modules.guardianprotection

import org.junit.Assert.assertEquals
import org.junit.Test

class ChildProtectionResetTest {
  @Test
  fun `reset tears down every child enforcement owner before re-pairing`() {
    val calls = mutableListOf<String>()
    ChildProtectionReset(
      stopVpn = { calls += "vpn" },
      clearPendingVpnEnable = { calls += "vpn-enable" },
      clearAccessibilityEnforcement = { calls += "accessibility" },
      dismissContentBlock = { calls += "block-activity" },
      clearContentPresentation = { calls += "block-presentation" },
      clearPolicyRuntime = { calls += "policy-runtime" },
      clearContentRuntime = { calls += "content-runtime" },
      clearPersistedPolicy = { calls += "encrypted-store" },
      revokeContentConsent = { calls += "content-consent" },
    ).reset()

    assertEquals(
      listOf(
        "vpn",
        "vpn-enable",
        "accessibility",
        "block-activity",
        "block-presentation",
        "policy-runtime",
        "content-runtime",
        "encrypted-store",
        "content-consent",
      ),
      calls,
    )
  }
}
