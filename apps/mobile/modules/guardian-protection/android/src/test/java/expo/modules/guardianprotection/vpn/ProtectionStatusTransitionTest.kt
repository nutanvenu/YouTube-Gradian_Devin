package expo.modules.guardianprotection.vpn

import org.junit.Assert.assertFalse
import org.junit.Assert.assertEquals
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

  @Test
  fun lateSubscriberReceivesCurrentStateOnceWithoutReemittingUnchangedState() {
    val replay = ProtectionStatusReplay()
    val received = mutableListOf<ProtectionStatusChange>()

    replay.emit(ProtectionStatusChange(active = true, details = null))
    replay.setListener { received += it }
    replay.emit(ProtectionStatusChange(active = true, details = "still-running"))
    replay.emit(ProtectionStatusChange(active = false, details = "VPN_STOPPED"))

    assertEquals(2, received.size)
    assertTrue(received[0].active)
    assertFalse(received[1].active)
  }
}
