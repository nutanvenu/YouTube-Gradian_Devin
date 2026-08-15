package expo.modules.guardianprotection.policy

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProtectionStatusEvaluatorTest {
  @Test
  fun cachedOrBootStartedVpnIsActiveWithoutAJsStartIntent() {
    val capabilities = mapOf(
      "vpn_filtering" to mapOf<String, Any?>("level" to "FULL"),
      "web_filtering" to mapOf<String, Any?>("level" to "LIMITED"),
    )

    val active = ProtectionStatusEvaluator.evaluate(true, 7L, capabilities)
    assertTrue(active["active"] as Boolean)
    assertEquals("HEALTHY", active["health"])

    val stopped = ProtectionStatusEvaluator.evaluate(false, 7L, capabilities)
    assertFalse(stopped["active"] as Boolean)
    assertEquals("DISABLED", stopped["health"])
  }
}
