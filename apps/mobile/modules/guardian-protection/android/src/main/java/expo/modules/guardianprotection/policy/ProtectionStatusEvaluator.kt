package expo.modules.guardianprotection.policy

internal object ProtectionStatusEvaluator {
  fun evaluate(
    active: Boolean,
    policyVersion: Long?,
    capabilities: Map<String, Map<String, Any?>>,
  ): Map<String, Any?> {
    val missing = capabilities.filterValues { it["level"] == "UNAVAILABLE" }.keys
    val health = when {
      !active -> "DISABLED"
      missing.isEmpty() -> "HEALTHY"
      else -> "DEGRADED"
    }
    return mapOf(
      "active" to active,
      "health" to health,
      "policyVersion" to policyVersion,
      "observedAt" to java.time.Instant.now().toString(),
      "details" to missing.takeIf { it.isNotEmpty() }?.joinToString(","),
    )
  }
}
