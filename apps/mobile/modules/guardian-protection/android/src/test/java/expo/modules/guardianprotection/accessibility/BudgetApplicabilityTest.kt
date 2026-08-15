package expo.modules.guardianprotection.accessibility

import expo.modules.guardianprotection.policy.CompiledPolicySnapshot
import java.time.Instant
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BudgetApplicabilityTest {
  private val now = Instant.parse("2026-01-01T12:00:00Z")

  @Test
  fun recognizesAppCategoryAndDeviceBudgets() {
    val snapshot = snapshot(
      appRules = mapOf("com.example.app" to mapOf("action" to "LIMIT", "daily_minutes" to 30)),
      categoryRules = mapOf("GAMES" to mapOf("action" to "LIMIT", "daily_minutes" to 45)),
      basePolicy = mapOf("daily_device_budget_minutes" to 60),
    )

    assertTrue(BudgetApplicability.hasApplicableAppBudget(snapshot, "com.example.app", "UNKNOWN", now))
    assertTrue(BudgetApplicability.hasApplicableAppBudget(snapshot, "com.example.game", "GAMES", now))
    assertTrue(BudgetApplicability.hasApplicableAppBudget(snapshot, "com.example.other", "UNKNOWN", now))
  }

  @Test
  fun ignoresNonBudgetRulesAndInactiveOverrides() {
    val snapshot = snapshot(
      appRules = mapOf("com.example.app" to mapOf("action" to "ALLOW")),
      temporaryOverrides = listOf(
        mapOf(
          "target_kind" to "APP",
          "target_ref" to "com.example.app",
          "action" to "LIMIT",
          "daily_minutes" to 30,
          "starts_at" to "2026-01-02T00:00:00Z",
          "expires_at" to "2026-01-03T00:00:00Z",
        ),
      ),
    )

    assertFalse(BudgetApplicability.hasApplicableAppBudget(snapshot, "com.example.app", "UNKNOWN", now))
  }

  private fun snapshot(
    appRules: Map<String, Map<String, Any?>> = emptyMap(),
    categoryRules: Map<String, Map<String, Any?>> = emptyMap(),
    temporaryOverrides: List<Map<String, Any?>> = emptyList(),
    basePolicy: Map<String, Any?> = emptyMap(),
  ) = CompiledPolicySnapshot(
    policyVersion = 1,
    appRules = appRules,
    domainRules = emptyList(),
    categoryRules = categoryRules,
    temporaryOverrides = temporaryOverrides,
    routines = emptyList(),
    basePolicy = basePolicy,
  )
}
