package expo.modules.guardianprotection

import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import expo.modules.guardianprotection.health.CapabilityDetector
import expo.modules.guardianprotection.policy.PolicyManager
import expo.modules.guardianprotection.storage.EncryptedPolicyStore
import java.time.Instant
import java.util.concurrent.atomic.AtomicReference

class GuardianProtectionModule : Module() {
  private val store by lazy { EncryptedPolicyStore(requireNotNull(appContext.reactContext)) }
  private val policyManager by lazy { PolicyManager(store, BuildConfig.GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS) }
  private val capabilities by lazy { CapabilityDetector(requireNotNull(appContext.reactContext)) }
  private val lastCapabilities = AtomicReference<Map<String, Map<String, Any?>>?>()

  override fun definition() = ModuleDefinition {
    Name("GuardianProtection")
    Events("onGuardianEvent")
    OnActivityEntersForeground {
      reportCapabilityChanges(capabilities.getCapabilities())
    }

    AsyncFunction("getCapabilities") {
      reportCapabilityChanges(capabilities.getCapabilities())
    }
    AsyncFunction("getProtectionStatus") {
      policyManager.protectionStatus(reportCapabilityChanges(capabilities.getCapabilities()))
    }
    AsyncFunction("requestVpnPermission") {
      capabilities.requestVpnPermission()
    }
    AsyncFunction("openUsageAccessSettings") {
      capabilities.openUsageAccessSettings()
    }
    AsyncFunction("openAccessibilitySettings") {
      capabilities.openAccessibilitySettings()
    }
    AsyncFunction("openNotificationAccessSettings") {
      capabilities.openNotificationAccessSettings()
    }
    AsyncFunction("startProtection") {
      policyManager.start()
      sendEvent("onGuardianEvent", mapOf(
        "type" to "PROTECTION_STATUS_CHANGED",
        "status" to policyManager.protectionStatus(reportCapabilityChanges(capabilities.getCapabilities())),
      ))
    }
    AsyncFunction("applyPolicyBundle") { bundle: Map<String, Any?> ->
      val result = policyManager.apply(bundle)
      if (result["applied"] == true) {
        sendEvent("onGuardianEvent", mapOf(
          "type" to "POLICY_APPLIED",
          "version" to result["policyVersion"],
        ))
      }
      result
    }
    AsyncFunction("getUsageSummary") { range: Map<String, Any?> ->
      store.usageSummary(range)
    }
    AsyncFunction("getObservedApps") {
      capabilities.observedApps()
    }
  }

  private fun reportCapabilityChanges(current: Map<String, Map<String, Any?>>): Map<String, Map<String, Any?>> {
    val previous = lastCapabilities.getAndSet(current)
    if (previous != null) {
      current.forEach { (capability, status) ->
        if (previous[capability] != status) {
          sendEvent("onGuardianEvent", mapOf(
            "type" to "PERMISSION_STATE_CHANGED",
            "capability" to capability,
            "state" to status["level"],
          ))
        }
      }
    }
    return current
  }
}
