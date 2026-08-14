package expo.modules.guardianprotection.policy

import expo.modules.guardianprotection.storage.EncryptedPolicyStore
import org.json.JSONObject
import java.time.Instant

class PolicyManager(
  private val store: EncryptedPolicyStore,
  trustedKeysJson: String = "{}",
) {
  private val verifier = PolicyVerifier(parseTrustedKeys(trustedKeysJson))
  @Volatile private var active: CompiledPolicySnapshot? = null
  @Volatile private var started = false

  init {
    store.active()?.let { active = null }
  }

  fun apply(bundle: Map<String, Any?>): Map<String, Any?> {
    val version = (bundle["policy_version"] as? Number)?.toLong()
      ?: return failure("INVALID_POLICY_VERSION")
    if ((bundle["schema_version"] as? Number)?.toInt() != 1) return failure("UNSUPPORTED_SCHEMA")
    val current = store.appliedVersion()
    if (current != null && version <= current) return failure("POLICY_VERSION_NOT_MONOTONIC", current)
    if (!verifier.verify(bundle)) return failure("SIGNATURE_INVALID", current)
    return runCatching {
      val compiled = compile(bundle)
      val previous = active
      store.swap(CanonicalJson.encode(bundle), version)
      active = compiled
      mapOf("applied" to true, "policyVersion" to version)
    }.getOrElse {
      active = active
      failure("POLICY_REJECTED")
    }
  }

  fun start() {
    started = true
  }

  fun protectionStatus(capabilities: Map<String, Map<String, Any?>>): Map<String, Any?> {
    val missing = capabilities.filterValues { it["level"] == "UNAVAILABLE" }.keys
    val health = when {
      !started -> "DISABLED"
      missing.isEmpty() -> "HEALTHY"
      else -> "DEGRADED"
    }
    return mapOf(
      "active" to started,
      "health" to health,
      "policyVersion" to (active?.policyVersion ?: store.appliedVersion()),
      "observedAt" to Instant.now().toString(),
      "details" to missing.takeIf { it.isNotEmpty() }?.joinToString(","),
    )
  }

  private fun compile(bundle: Map<String, Any?>): CompiledPolicySnapshot {
    val appRules = (bundle["app_rules"] as? List<*>).orEmpty()
      .filterIsInstance<Map<*, *>>()
      .mapNotNull { rule -> (rule["app_ref"] as? String)?.let { it to rule.cast() } }
      .toMap()
    val categoryRules = (bundle["category_rules"] as? List<*>).orEmpty()
      .filterIsInstance<Map<*, *>>()
      .mapNotNull { rule -> (rule["category"] as? String)?.let { it to rule.cast() } }
      .toMap()
    return CompiledPolicySnapshot(
      policyVersion = (bundle["policy_version"] as Number).toLong(),
      appRules = appRules,
      domainRules = (bundle["domain_rules"] as? List<*>)?.filterIsInstance<Map<*, *>>()?.map { it.cast() }.orEmpty(),
      categoryRules = categoryRules,
      temporaryOverrides = (bundle["temporary_overrides"] as? List<*>)?.filterIsInstance<Map<*, *>>()?.map { it.cast() }.orEmpty(),
      routines = (bundle["routines"] as? List<*>)?.filterIsInstance<Map<*, *>>()?.map { it.cast() }.orEmpty(),
      basePolicy = (bundle["base_policy"] as? Map<*, *>)?.cast() ?: emptyMap(),
    )
  }

  private fun failure(reason: String, version: Long? = null) = mapOf(
    "applied" to false,
    "policyVersion" to version,
    "reason" to reason,
  )

  private fun Map<*, *>.cast(): Map<String, Any?> =
    entries.associate { (key, value) -> key as String to value }

  private fun parseTrustedKeys(value: String): Map<String, String> {
    return runCatching {
      val json = JSONObject(value)
      json.keys().asSequence().associateWith { key -> json.getString(key) }
    }.getOrDefault(emptyMap())
  }
}
