package expo.modules.guardianprotection.policy

data class CompiledPolicySnapshot(
  val policyVersion: Long,
  val appRules: Map<String, Map<String, Any?>>,
  val domainRules: List<Map<String, Any?>>,
  val categoryRules: Map<String, Map<String, Any?>>,
  val temporaryOverrides: List<Map<String, Any?>>,
  val routines: List<Map<String, Any?>>,
  val basePolicy: Map<String, Any?>,
)
