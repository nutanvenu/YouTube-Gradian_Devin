package expo.modules.guardianprotection

import org.junit.Assert.assertEquals
import org.junit.Test

class CapabilityStateComparisonTest {
  @Test
  fun unchangedCapabilityIgnoresObservationTimestamp() {
    val previous = mapOf("app_blocking" to status("FULL", "Accessibility app blocking", "old"))
    val current = mapOf("app_blocking" to status("FULL", "Accessibility app blocking", "new"))

    assertEquals(emptySet<String>(), CapabilityStateComparison.changedCapabilities(previous, current))
  }

  @Test
  fun levelChangeEmitsCapabilityChange() {
    val previous = mapOf("app_blocking" to status("FULL", "Accessibility app blocking", "old"))
    val current = mapOf("app_blocking" to status("UNAVAILABLE", "Accessibility permission", "new"))

    assertEquals(setOf("app_blocking"), CapabilityStateComparison.changedCapabilities(previous, current))
  }

  @Test
  fun detailOnlyChangeEmitsCapabilityChange() {
    val previous = mapOf("app_blocking" to status("UNAVAILABLE", "Accessibility permission", "old"))
    val current = mapOf("app_blocking" to status("UNAVAILABLE", "Accessibility app blocking", "new"))

    assertEquals(setOf("app_blocking"), CapabilityStateComparison.changedCapabilities(previous, current))
  }

  @Test
  fun capabilityAppearingOrDisappearingEmitsCapabilityChange() {
    val previous = mapOf("app_blocking" to status("FULL", "Accessibility app blocking", "old"))
    val appeared = mapOf(
      "app_blocking" to status("FULL", "Accessibility app blocking", "new"),
      "web_filtering" to status("LIMITED", "DNS filtering", "new"),
    )
    val disappeared = mapOf("web_filtering" to status("LIMITED", "DNS filtering", "new"))

    assertEquals(setOf("web_filtering"), CapabilityStateComparison.changedCapabilities(previous, appeared))
    assertEquals(setOf("app_blocking"), CapabilityStateComparison.changedCapabilities(appeared, disappeared))
  }

  @Test
  fun firstObservationDoesNotEmitChanges() {
    val current = mapOf("app_blocking" to status("FULL", "Accessibility app blocking", "now"))

    assertEquals(emptySet<String>(), CapabilityStateComparison.changedCapabilities(null, current))
  }

  private fun status(level: String, detail: String, updatedAt: String) = mapOf(
    "level" to level,
    "detail" to detail,
    "updatedAt" to updatedAt,
  )
}
