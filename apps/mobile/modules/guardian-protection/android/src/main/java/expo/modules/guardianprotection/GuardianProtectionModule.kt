package expo.modules.guardianprotection

import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import expo.modules.guardianprotection.health.CapabilityDetector
import expo.modules.guardianprotection.policy.PolicyManager
import expo.modules.guardianprotection.policy.GuardianPolicyRuntime
import expo.modules.guardianprotection.storage.EncryptedPolicyStore
import expo.modules.guardianprotection.reputation.EncryptedReputationStore
import expo.modules.guardianprotection.reputation.ReputationManager
import expo.modules.guardianprotection.policy.PolicyVerifier
import expo.modules.guardianprotection.usage.UsageCollector
import expo.modules.guardianprotection.vpn.GuardianVpnService
import expo.modules.guardianprotection.communication.CommunicationSafetyRuntime
import java.time.Instant
import java.util.concurrent.atomic.AtomicReference

class GuardianProtectionModule : Module() {
  private val store by lazy { EncryptedPolicyStore(requireNotNull(appContext.reactContext)) }
  private val policyManager by lazy { PolicyManager(store, BuildConfig.GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS) }
  private val reputationManager by lazy {
    val verifier = PolicyVerifier(parseTrustedKeys(BuildConfig.GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS))
    ReputationManager(EncryptedReputationStore(requireNotNull(appContext.reactContext))) { verifier.verify(it) }
  }
  private val capabilities by lazy { CapabilityDetector(requireNotNull(appContext.reactContext)) }
  private val usage by lazy { UsageCollector(requireNotNull(appContext.reactContext), store) }
  private val lastCapabilities = AtomicReference<Map<String, Map<String, Any?>>?>()

  override fun definition() = ModuleDefinition {
    Name("GuardianProtection")
    Events("onGuardianEvent")
    OnActivityEntersForeground {
      installCommunicationListener()
      reportCapabilityChanges(capabilities.getCapabilities())
    }

    AsyncFunction("getCapabilities") {
      installCommunicationListener()
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
      installCommunicationListener()
      GuardianPolicyRuntime.install(policyManager)
      GuardianPolicyRuntime.installReputation(reputationManager)
      GuardianPolicyRuntime.addListener(eventListener)
      policyManager.start()
      if (capabilities.getCapabilities()["app_usage"]?.get("level") == "FULL") {
        usage.refresh()
      }
      GuardianVpnService.start(requireNotNull(appContext.reactContext))
      sendEvent("onGuardianEvent", mapOf(
        "type" to "PROTECTION_STATUS_CHANGED",
        "status" to policyManager.protectionStatus(reportCapabilityChanges(capabilities.getCapabilities())),
      ))
    }
    AsyncFunction("stopProtection") {
      GuardianVpnService.stop(requireNotNull(appContext.reactContext))
      sendEvent("onGuardianEvent", mapOf(
        "type" to "PROTECTION_STATUS_CHANGED",
        "status" to mapOf(
          "active" to false,
          "health" to "DEGRADED",
          "policyVersion" to policyManager.activeSnapshot()?.policyVersion,
          "observedAt" to Instant.now().toString(),
          "details" to "STOPPED_BY_PARENT",
        ),
      ))
    }
    AsyncFunction("applyPolicyBundle") { bundle: Map<String, Any?> ->
      GuardianPolicyRuntime.install(policyManager)
      val result = policyManager.apply(bundle)
      if (result["applied"] == true) {
        sendEvent("onGuardianEvent", mapOf(
          "type" to "POLICY_APPLIED",
          "version" to result["policyVersion"],
        ))
      }
      result
    }
    AsyncFunction("applyReputationBundle") { bundle: Map<String, Any?> ->
      GuardianPolicyRuntime.installReputation(reputationManager)
      val result = reputationManager.apply(bundle)
      sendEvent("onGuardianEvent", mapOf(
        "type" to "REPUTATION_STATUS_CHANGED",
        "version" to result.version,
        "reason" to result.reason,
      ))
      mapOf(
        "applied" to result.applied,
        "version" to result.version,
        "reason" to result.reason,
        "entryCount" to result.entryCount,
        "encodedBytes" to result.encodedBytes,
        "applyMillis" to result.applyMillis,
        "estimatedMemoryBytes" to result.estimatedMemoryBytes,
      )
    }
    AsyncFunction("getReputationStatus") {
      mapOf(
        "version" to reputationManager.version(),
        "entryCount" to (reputationManager.snapshot()?.entries?.size ?: 0),
        "pending" to (reputationManager.snapshot()?.entries?.values?.count { it.verdict == "UNKNOWN" } ?: 0),
      )
    }
    AsyncFunction("getUsageSummary") { range: Map<String, Any?> ->
      if (capabilities.getCapabilities()["app_usage"]?.get("level") == "FULL") {
        usage.refresh()
      }
      usage.summary(range)
    }
    AsyncFunction("getObservedApps") {
      capabilities.observedApps()
    }
    AsyncFunction("markObservedAppReviewed") { packageName: String ->
      capabilities.markObservedAppReviewed(packageName)
    }
  }

  private fun parseTrustedKeys(value: String): Map<String, String> {
    return runCatching {
      val json = org.json.JSONObject(value)
      json.keys().asSequence().associateWith { key -> json.getString(key) }
    }.getOrDefault(emptyMap())
  }

  private val eventListener = object : GuardianPolicyRuntime.Listener {
    override fun onWebBlocked(domain: String, category: String?, appRef: String?, reasonCode: String) {
      sendEvent("onGuardianEvent", mapOf(
        "type" to "WEB_BLOCKED",
        "domain" to domain,
        "category" to category,
        "appRef" to appRef,
        "reasonCode" to reasonCode,
      ))
    }

    override fun onVpnFailure(reason: String) {
      sendEvent("onGuardianEvent", mapOf(
        "type" to "PROTECTION_STATUS_CHANGED",
        "status" to mapOf(
          "active" to false,
          "health" to "DEGRADED",
          "policyVersion" to policyManager.activeSnapshot()?.policyVersion,
          "observedAt" to Instant.now().toString(),
          "details" to reason,
        ),
      ))
    }

    override fun onAppBlocked(packageName: String, reasonCode: String) {
      sendEvent("onGuardianEvent", mapOf(
        "type" to "APP_BLOCKED",
        "appRef" to packageName,
        "reasonCode" to reasonCode,
      ))
    }

    override fun onTimeWarning(targetRef: String, remainingSeconds: Long) {
      sendEvent("onGuardianEvent", mapOf(
        "type" to "TIME_WARNING",
        "targetRef" to targetRef,
        "remainingSeconds" to remainingSeconds,
      ))
    }

    override fun onTimeExpired(targetRef: String) {
      sendEvent("onGuardianEvent", mapOf(
        "type" to "TIME_EXPIRED",
        "targetRef" to targetRef,
      ))
    }
  }

  private fun installCommunicationListener() {
    CommunicationSafetyRuntime.setListener { signal, packageName ->
      sendEvent("onGuardianEvent", mapOf(
        "type" to "SAFETY_EVENT",
        "category" to signal.category,
        "severity" to signal.severity,
        "reasonCode" to signal.reasonCode,
        "appRef" to packageName,
      ))
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
