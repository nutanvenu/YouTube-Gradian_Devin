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
}
