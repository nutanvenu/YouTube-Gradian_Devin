package expo.modules.guardianprotection.policy

import java.time.Instant
import org.junit.Assert.assertEquals
import org.junit.Test

class PolicyEvaluatorTest {
  private val evaluator = PolicyEvaluator()

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
}
