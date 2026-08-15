package expo.modules.guardianprotection.vpn

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProtectionStatusTransitionTest {
  @Test
  fun emitsForFirstActiveObservationAndRealStateChangesOnly() {
    assertTrue(ProtectionStatusTransition.shouldEmit(null, true))
    assertFalse(ProtectionStatusTransition.shouldEmit(true, true))
    assertTrue(ProtectionStatusTransition.shouldEmit(true, false))
    assertFalse(ProtectionStatusTransition.shouldEmit(false, false))
  }
}
