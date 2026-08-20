package expo.modules.guardianprotection.health

import org.junit.Assert.assertEquals
import org.junit.Test

class AccessibilitySignalCapabilityTest {
  @Test fun `requires a usable signed parent policy after permission and consent`() {
    assertEquals(
      "UNAVAILABLE",
      AccessibilitySignalCapabilityEvaluator.evaluate(true, true, false).level,
    )
    assertEquals(
      "BEST_EFFORT",
      AccessibilitySignalCapabilityEvaluator.evaluate(true, true, true).level,
    )
  }

  @Test fun `reports the missing local consent before policy state`() {
    val capability = AccessibilitySignalCapabilityEvaluator.evaluate(true, false, false)

    assertEquals("UNAVAILABLE", capability.level)
    assertEquals(
      "Requires separate Content Safety consent on this child device.",
      capability.detail,
    )
  }
}
