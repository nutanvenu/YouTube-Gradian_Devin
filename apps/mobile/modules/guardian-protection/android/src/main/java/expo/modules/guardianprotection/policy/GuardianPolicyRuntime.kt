package expo.modules.guardianprotection.policy

import java.util.concurrent.CopyOnWriteArraySet

object GuardianPolicyRuntime {
  private var manager: PolicyManager? = null
  private val listeners = CopyOnWriteArraySet<Listener>()

  fun install(policyManager: PolicyManager) {
    manager = policyManager
  }

  fun hasActiveSnapshot(): Boolean = manager?.activeSnapshot() != null

  fun addListener(listener: Listener) {
    listeners += listener
  }

  fun evaluateDomain(domain: String, destinationIp: String? = null): DomainDecision {
    val current = manager?.activeSnapshot()
      ?: return DomainDecision(false, "POLICY_UNAVAILABLE")
    val result = current.let {
      PolicyEvaluator().evaluate(
        it,
        PolicyContext(
          now = java.time.Instant.now(),
          childId = "",
          packageName = null,
          domain = domain,
          destinationIp = destinationIp,
          usageTodayMs = 0,
          sessionMs = null,
          activeRoutineIds = emptySet(),
          signal = null,
        ),
      )
    }
    val category = current.domainTrie.match(domain)?.get("category") as? String
    return DomainDecision(result.action == "BLOCK" || result.action == "LIMIT_REACHED", result.reasonCode, category)
  }

  fun reportBlocked(domain: String, reasonCode: String, category: String? = null, appRef: String? = null) {
    listeners.forEach { it.onWebBlocked(domain, category, appRef, reasonCode) }
  }

  fun reportFailure(reason: String) {
    listeners.forEach { it.onVpnFailure(reason) }
  }

  data class DomainDecision(val blocked: Boolean, val reasonCode: String, val category: String? = null)

  interface Listener {
    fun onWebBlocked(domain: String, category: String?, appRef: String?, reasonCode: String)
    fun onVpnFailure(reason: String)
  }
}
