package expo.modules.guardianprotection.policy

import java.time.Instant
import org.junit.Assert.assertEquals
import org.junit.Test

class PolicyEvaluatorTest {
  private val evaluator = PolicyEvaluator()

  @Test
  fun categoryBudgetUsesAggregateCategoryUsageAcrossApps() {
    val snapshot = CompiledPolicySnapshot(
      policyVersion = 3,
      appRules = emptyMap(), domainRules = emptyList(),
      categoryRules = mapOf("VIDEO" to mapOf("action" to "LIMIT", "daily_minutes" to 20)),
      temporaryOverrides = emptyList(), routines = emptyList(),
      basePolicy = mapOf("unknown_app_policy" to "ALLOW_AND_NOTIFY"),
    )
    val context = PolicyContext(
      now = Instant.parse("2026-01-01T12:00:00Z"), childId = "child",
      packageName = "com.example.video", domain = null, destinationIp = null,
      usageTodayMs = 60_000, sessionMs = null, activeRoutineIds = emptySet(), signal = null,
      category = "VIDEO", categoryUsageTodayMs = 1_200_000,
    )
    assertEquals("LIMIT_REACHED", evaluator.evaluate(snapshot, context).action)
    assertEquals("ALLOW_WITH_BUDGET", evaluator.evaluate(snapshot, context.copy(categoryUsageTodayMs = 1_199_000)).action)
  }

  @Test
  fun categoryBlockAppliesToAppsUnlessAnExplicitAppRuleOverridesIt() {
    val snapshot = CompiledPolicySnapshot(
      policyVersion = 3, appRules = emptyMap(), domainRules = emptyList(),
      categoryRules = mapOf("VIDEO" to mapOf("action" to "BLOCK")),
      temporaryOverrides = emptyList(), routines = emptyList(),
      basePolicy = mapOf("unknown_app_policy" to "ALLOW_AND_NOTIFY"),
    )
    val context = PolicyContext(
      now = Instant.parse("2026-01-01T12:00:00Z"), childId = "child",
      packageName = "com.example.video", domain = null, destinationIp = null,
      usageTodayMs = 0, sessionMs = null, activeRoutineIds = emptySet(), signal = null,
      category = "VIDEO", categoryUsageTodayMs = 0,
    )
    assertEquals("BLOCK", evaluator.evaluate(snapshot, context).action)
    assertEquals("ALLOW", evaluator.evaluate(snapshot.copy(appRules = mapOf("com.example.video" to mapOf("action" to "ALLOW"))), context).action)
  }

  @Test
  fun explicitAppBlockWinsOverDefaultAllow() {
    val snapshot = CompiledPolicySnapshot(
      policyVersion = 7,
      appRules = mapOf("com.example.blocked" to mapOf("action" to "BLOCK")),
      domainRules = emptyList(),
      categoryRules = emptyMap(),
      temporaryOverrides = emptyList(),
      routines = emptyList(),
      basePolicy = mapOf("unknown_domain_policy" to "ALLOW_AND_NOTIFY"),
    )
    val decision = evaluator.evaluate(
      snapshot,
      PolicyContext(Instant.parse("2026-01-01T00:00:00Z"), "child", "com.example.blocked", null, null, null, null, emptySet(), null),
    )
    assertEquals("BLOCK", decision.action)
    assertEquals("EXPLICIT_TARGET_RULE", decision.reasonCode)
    assertEquals(7, decision.policyVersion)
  }

  @Test
  fun unknownDomainUsesBasePolicy() {
    val snapshot = CompiledPolicySnapshot(
      policyVersion = 2,
      appRules = emptyMap(),
      domainRules = emptyList(),
      categoryRules = emptyMap(),
      temporaryOverrides = emptyList(),
      routines = emptyList(),
      basePolicy = mapOf("unknown_domain_policy" to "BLOCK_WHILE_CLASSIFYING"),
    )
    val decision = evaluator.evaluate(
      snapshot,
      PolicyContext(Instant.parse("2026-01-01T00:00:00Z"), "child", null, "unknown.example", null, null, null, emptySet(), null),
    )
    assertEquals("BLOCK", decision.action)
    assertEquals("UNKNOWN_DOMAIN_POLICY", decision.reasonCode)
  }

  @Test
  fun activeManualRoutineFromLocalPolicyContextWins() {
    val snapshot = CompiledPolicySnapshot(
      policyVersion = 8,
      appRules = emptyMap(),
      domainRules = emptyList(),
      categoryRules = emptyMap(),
      temporaryOverrides = emptyList(),
      routines = listOf(
        mapOf(
          "routine_id" to "focus",
          "kind" to "MANUAL",
          "blocked_apps" to listOf("com.example.video"),
        ),
      ),
      basePolicy = mapOf(
        "unknown_app_policy" to "ALLOW_AND_NOTIFY",
        "current_manual_routine_id" to "focus",
      ),
    )
    val decision = evaluator.evaluate(
      snapshot,
      PolicyContext(
        Instant.parse("2026-01-01T00:00:00Z"),
        "child",
        "com.example.video",
        null,
        null,
        0,
        null,
        emptySet(),
        null,
        null,
        0,
        "focus",
        "UTC",
      ),
    )
    assertEquals("BLOCK", decision.action)
    assertEquals("MANUAL_ROUTINE", decision.reasonCode)
  }

  @Test
  fun activeDeviceTimeExtensionRaisesBudget() {
    val snapshot = CompiledPolicySnapshot(
      policyVersion = 9,
      appRules = emptyMap(),
      domainRules = emptyList(),
      categoryRules = emptyMap(),
      temporaryOverrides = listOf(
        mapOf(
          "target_kind" to "DEVICE",
          "starts_at" to "2026-01-01T00:00:00Z",
          "expires_at" to "2026-01-02T00:00:00Z",
          "daily_minutes" to 75,
        ),
      ),
      routines = emptyList(),
      basePolicy = mapOf(
        "daily_device_budget_minutes" to 60,
        "unknown_app_policy" to "ALLOW_AND_NOTIFY",
      ),
    )
    val decision = evaluator.evaluate(
      snapshot,
      PolicyContext(
        Instant.parse("2026-01-01T12:00:00Z"),
        "child",
        "com.example.video",
        null,
        null,
        0,
        null,
        emptySet(),
        null,
        null,
        4_400_000,
      ),
    )
    assertEquals("ALLOW", decision.action)
  }
}
