package expo.modules.guardianprotection.vpn

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CachedProtectionStartupTest {
  @Test
  fun startsOnlyWhenProtectionWasEnabledSnapshotExistsAndConsentIsGranted() {
    assertTrue(
      CachedProtectionStartup.shouldStart(
        protectionEnabled = true,
        hasVerifiedSnapshot = true,
        vpnConsentGranted = true,
      ),
    )
    assertFalse(
      CachedProtectionStartup.shouldStart(
        protectionEnabled = false,
        hasVerifiedSnapshot = true,
        vpnConsentGranted = true,
      ),
    )
    assertFalse(
      CachedProtectionStartup.shouldStart(
        protectionEnabled = true,
        hasVerifiedSnapshot = false,
        vpnConsentGranted = true,
      ),
    )
    assertFalse(
      CachedProtectionStartup.shouldStart(
        protectionEnabled = true,
        hasVerifiedSnapshot = true,
        vpnConsentGranted = false,
      ),
    )
  }

  @Test
  fun userInitiatedEnableHasItsOwnIntentGateWithoutWeakeningSilentRestore() {
    assertTrue(UserInitiatedProtectionStartup.shouldStart(true, true))
    assertFalse(UserInitiatedProtectionStartup.shouldStart(false, true))
    assertFalse(UserInitiatedProtectionStartup.shouldStart(true, false))

    assertFalse(
      CachedProtectionStartup.shouldStart(
        protectionEnabled = false,
        hasVerifiedSnapshot = true,
        vpnConsentGranted = true,
      ),
    )
  }
}
