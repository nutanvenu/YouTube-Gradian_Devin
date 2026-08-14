package expo.modules.guardianprotection.policy

import java.time.Instant

data class PolicyContext(
  val now: Instant,
  val childId: String,
  val packageName: String?,
  val domain: String?,
  val destinationIp: String?,
  val usageTodayMs: Long?,
  val sessionMs: Long?,
  val activeRoutineIds: Set<String>,
  val signal: String?,
)

data class PolicyDecision(
  val action: String,
  val reasonCode: String,
  val expiresAt: Instant?,
  val policyVersion: Long,
)

class PolicyEvaluator {
  fun evaluate(snapshot: CompiledPolicySnapshot, context: PolicyContext): PolicyDecision {
    val appRule = context.packageName?.let(snapshot.appRules::get)
    if (appRule != null) return decision(appRule, snapshot.policyVersion)
    val domainRule = context.domain?.let { domain ->
      snapshot.domainRules.firstOrNull { rule ->
        val configured = rule["domain"] as? String ?: return@firstOrNull false
        val match = rule["match"] as? String ?: "EXACT"
        domain == configured || (match == "SUBDOMAINS" && domain.endsWith(".$configured"))
      }
    }
    if (domainRule != null) return decision(domainRule, snapshot.policyVersion)
    val unknownDomain = snapshot.basePolicy["unknown_domain_policy"] as? String
    if (context.domain != null && unknownDomain?.startsWith("BLOCK") == true) {
      return PolicyDecision("BLOCK", "UNKNOWN_DOMAIN_POLICY", null, snapshot.policyVersion)
    }
    return PolicyDecision("ALLOW", "DEFAULT_ALLOW", null, snapshot.policyVersion)
  }

  private fun decision(rule: Map<String, Any?>, version: Long) = when (rule["action"] as? String) {
    "BLOCK", "ASK_PARENT" -> PolicyDecision("BLOCK", if (rule["action"] == "ASK_PARENT") "REQUIRES_PARENT_APPROVAL" else "EXPLICIT_TARGET_RULE", null, version)
    "LIMIT" -> PolicyDecision("ALLOW_WITH_BUDGET", "BUDGET_AVAILABLE", null, version)
    else -> PolicyDecision("ALLOW", "EXPLICIT_TARGET_RULE", null, version)
  }
}
