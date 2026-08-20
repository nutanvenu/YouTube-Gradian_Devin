package expo.modules.guardianprotection.content

import java.time.Instant
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ContentBlockStateTest {
  private val now = Instant.parse("2026-08-16T12:00:00Z")
  private val event = MinimizedContentRiskEvent(
    source = SignalSource.ACCESSIBILITY_TEXT,
    appRef = "com.future.video",
    fingerprint = "a".repeat(64),
    category = ContentRiskCategory.SELF_HARM_SUICIDE,
    severity = ContentRiskSeverity.CRITICAL,
    confidence = 0.94,
    reasonCode = "SELF_HARM_DIRECT+SELF_HARM_INTENT",
    classifierVersion = "deterministic-rules-v1",
    capabilityLevel = ContentCapabilityLevel.BEST_EFFORT,
    action = ContentAction.BLOCK_AND_REQUEST,
  )

  @Test
  fun `offline or denied content remains blocked without an implicit parent request`() {
    val decision = ContentBlockStateMachine.decide(event, null, emptyList(), "device-a", now)
    assertTrue(decision.shouldBlock)
    assertFalse(decision.reference.toString().contains("RAW-CANARY"))
    val repeated = ContentBlockStateMachine.decide(event, decision.reference, emptyList(), "device-a", now)
    assertTrue(repeated.shouldBlock)
  }

  @Test
  fun `approval unlocks only the exact device app fingerprint until expiry`() {
    val exact = ContentApproval("device-a", event.appRef, event.fingerprint, now.plusSeconds(900))
    assertFalse(ContentBlockStateMachine.decide(event, null, listOf(exact), "device-a", now).shouldBlock)
    assertTrue(ContentBlockStateMachine.decide(event, null, listOf(exact), "device-b", now).shouldBlock)
    assertTrue(ContentBlockStateMachine.decide(event.copy(fingerprint = "b".repeat(64)), null, listOf(exact), "device-a", now).shouldBlock)
    assertTrue(ContentBlockStateMachine.decide(event, null, listOf(exact), "device-a", now.plusSeconds(900)).shouldBlock)
  }

  @Test
  fun `system emergency settings launcher and Guardian are never content blocked`() {
    assertFalse(ContentBlockEligibility.mayBlock("com.android.settings", "com.guardian.family"))
    assertFalse(ContentBlockEligibility.mayBlock("com.android.launcher3", "com.guardian.family"))
    assertFalse(ContentBlockEligibility.mayBlock("com.google.android.dialer", "com.guardian.family"))
    assertFalse(ContentBlockEligibility.mayBlock("com.guardian.family", "com.guardian.family"))
    assertFalse(ContentBlockEligibility.mayBlock("com.vendor.preinstalled.browser", "com.guardian.family", isSystemOrUpdated = true))
    assertTrue(ContentBlockEligibility.mayBlock("com.future.video", "com.guardian.family"))
  }

  @Test
  fun `background notification evidence cannot become a future active content block`() {
    assertFalse(ContentBlockEnforcementGate.mayPersistActiveBlock(event.copy(source = SignalSource.NOTIFICATION), false))
    assertFalse(ContentBlockEnforcementGate.mayPersistActiveBlock(event.copy(source = SignalSource.NOTIFICATION), true))
    assertTrue(ContentBlockEnforcementGate.mayPersistActiveBlock(event, true))
    assertTrue(ContentBlockEnforcementGate.mayPersistActiveBlock(event.copy(source = SignalSource.MEDIA_METADATA), true))
  }
}
