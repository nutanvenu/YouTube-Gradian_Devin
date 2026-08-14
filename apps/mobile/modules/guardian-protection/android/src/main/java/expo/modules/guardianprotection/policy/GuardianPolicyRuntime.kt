package expo.modules.guardianprotection.policy

import java.util.concurrent.CopyOnWriteArraySet

object GuardianPolicyRuntime {
  private var manager: PolicyManager? = null
  private val listeners = CopyOnWriteArraySet<Listener>()

  fun install(policyManager: PolicyManager) {
    manager = policyManager
  }

  fun addListener(listener: Listener) {
    listeners += listener
  }

  fun evaluateDomain(domain: String): DomainDecision {
    val current = manager?.activeSnapshot()
      ?: return DomainDecision(true, "UNKNOWN_DOMAIN_POLICY")
    val result = current.let {
      PolicyEvaluator().evaluate(
        it,
        PolicyContext(
          now = java.time.Instant.now(),
          childId = "",
          packageName = null,
          domain = domain,
          destinationIp = null,
          usageTodayMs = 0,
          sessionMs = null,
          activeRoutineIds = emptySet(),
          signal = null,
        ),
      )
    }
    return DomainDecision(result.action == "BLOCK" || result.action == "LIMIT_REACHED", result.reasonCode)
  }

  fun reportBlocked(domain: String, reasonCode: String) {
    listeners.forEach { it.onWebBlocked(domain, reasonCode) }
  }

  fun reportFailure(reason: String) {
    listeners.forEach { it.onVpnFailure(reason) }
  }

  data class DomainDecision(val blocked: Boolean, val reasonCode: String)

  interface Listener {
    fun onWebBlocked(domain: String, reasonCode: String)
    fun onVpnFailure(reason: String)
  }
}
