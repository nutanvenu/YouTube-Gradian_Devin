package expo.modules.guardianprotection.policy

internal object ProtectionStatusEvaluator {
  fun evaluate(
    active: Boolean,
    policyVersion: Long?,
    capabilities: Map<String, Map<String, Any?>>,
  ): Map<String, Any?> {
    val nonFull = capabilities.filterValues { it["level"] != "FULL" }.keys
    val health = when {
      !active -> "DISABLED"
      nonFull.isEmpty() -> "HEALTHY"
      else -> "DEGRADED"
    }
    return mapOf(
      "active" to active,
      "health" to health,
      "policyVersion" to policyVersion,
      "observedAt" to java.time.Instant.now().toString(),
      "details" to nonFull.takeIf { it.isNotEmpty() }?.joinToString(","),
    )
  }
}
