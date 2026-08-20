package expo.modules.guardianprotection.vpn

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GuardianVpnRuntimeStatusTest {
  @Test
  fun onlyAFormerRunningStateCanBecomeStaleAfterForceStopOrReboot() {
    assertTrue(GuardianVpnRuntimeStatus(GuardianVpnRuntimeState.RUNNING, null, 1_000L).isStale(301_001L))
    assertFalse(GuardianVpnRuntimeStatus(GuardianVpnRuntimeState.STOPPED, null, 1_000L).isStale(301_001L))
    assertFalse(GuardianVpnRuntimeStatus(GuardianVpnRuntimeState.RUNNING, null, null).isStale(301_001L))
  }
}
