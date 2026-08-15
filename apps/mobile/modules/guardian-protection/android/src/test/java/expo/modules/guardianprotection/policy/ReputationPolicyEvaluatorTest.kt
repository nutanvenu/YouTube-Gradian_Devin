package expo.modules.guardianprotection.policy

import java.time.Instant
import org.junit.Assert.assertEquals
import org.junit.Test

class ReputationPolicyEvaluatorTest {
  @Test
  fun explicitParentBlockOutranksKnownSafeReputation() {
    val snapshot = CompiledPolicySnapshot(
      policyVersion = 1,
      appRules = emptyMap(),
      domainRules = listOf(mapOf("domain" to "safe.example", "action" to "BLOCK", "rule_id" to "parent-block")),
      categoryRules = emptyMap(),
      temporaryOverrides = emptyList(),
      routines = emptyList(),
      basePolicy = mapOf("unknown_domain_policy" to "ALLOW_AND_NOTIFY"),
    )
    val decision = PolicyEvaluator().evaluate(
      snapshot,
      PolicyContext(
        now = Instant.parse("2026-01-01T00:00:00Z"),
        childId = "child",
        packageName = null,
        domain = "safe.example",
        destinationIp = null,
        usageTodayMs = null,
        sessionMs = null,
        activeRoutineIds = emptySet(),
        signal = null,
        reputationVerdict = "KNOWN_SAFE",
      ),
    )
    assertEquals("BLOCK", decision.action)
    assertEquals("EXPLICIT_TARGET_RULE", decision.reasonCode)
  }

  @Test
  fun youngerBandBlocksWhileUnknownClassificationIsPending() {
    val snapshot = CompiledPolicySnapshot(
      policyVersion = 1,
      appRules = emptyMap(),
      domainRules = emptyList(),
      categoryRules = emptyMap(),
      temporaryOverrides = emptyList(),
      routines = emptyList(),
      basePolicy = mapOf("unknown_domain_policy" to "BLOCK_WHILE_CLASSIFYING"),
    )
    val decision = PolicyEvaluator().evaluate(
      snapshot,
      PolicyContext(
        now = Instant.parse("2026-01-01T00:00:00Z"),
        childId = "child",
        packageName = null,
        domain = "unknown.example",
        destinationIp = null,
        usageTodayMs = null,
        sessionMs = null,
        activeRoutineIds = emptySet(),
        signal = null,
        reputationVerdict = null,
        reputationPendingUntil = Instant.parse("2026-01-01T00:05:00Z"),
      ),
    )
    assertEquals("BLOCK", decision.action)
    assertEquals("REPUTATION_PENDING", decision.reasonCode)
  }
}
