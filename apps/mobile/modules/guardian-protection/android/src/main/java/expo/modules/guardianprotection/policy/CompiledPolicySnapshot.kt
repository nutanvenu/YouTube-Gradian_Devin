package expo.modules.guardianprotection.policy

import java.time.Instant
import expo.modules.guardianprotection.content.ContentRiskSeverity

data class CompiledPolicySnapshot(
  val policyVersion: Long,
  val appRules: Map<String, Map<String, Any?>>,
  val domainRules: List<Map<String, Any?>>,
  val categoryRules: Map<String, Map<String, Any?>>,
  val temporaryOverrides: List<Map<String, Any?>>,
  val routines: List<Map<String, Any?>>,
  val basePolicy: Map<String, Any?>,
  val communicationSafety: Map<String, Any?> = emptyMap(),
  val domainTrie: DomainRuleTrie = DomainRuleTrie(domainRules),
  val expiresSoftAt: Instant? = null,
  val contentBlockThreshold: ContentRiskSeverity = ContentRiskSeverity.HIGH,
)
