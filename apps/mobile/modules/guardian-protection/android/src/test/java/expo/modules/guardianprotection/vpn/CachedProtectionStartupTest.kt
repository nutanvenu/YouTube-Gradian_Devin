package expo.modules.guardianprotection.vpn

import org.junit.Assert.assertFalse
import org.junit.Assert.assertEquals
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

  @Test
  fun deferredEnableIntentStaysUntilConsentThenExpiresAfterFiveMinutes() {
    val now = 10_000L
    assertEquals(
      UserInitiatedEnableIntentAction.KEEP,
      UserInitiatedEnableIntent.action(now - 1_000L, now, consentGranted = false),
    )
    assertEquals(
      UserInitiatedEnableIntentAction.CONSUME,
      UserInitiatedEnableIntent.action(now - 1_000L, now, consentGranted = true),
    )
    assertEquals(
      UserInitiatedEnableIntentAction.EXPIRE,
      UserInitiatedEnableIntent.action(
        now - UserInitiatedEnableIntent.MAX_AGE_MILLIS - 1L,
        now,
        consentGranted = false,
      ),
    )
    assertEquals(
      UserInitiatedEnableIntentAction.EXPIRE,
      UserInitiatedEnableIntent.action(now + 1L, now, consentGranted = true),
    )
  }
}
