package expo.modules.guardianprotection.accessibility

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import android.content.Intent
import expo.modules.guardianprotection.inventory.PackageInventory
import expo.modules.guardianprotection.policy.GuardianPolicyRuntime
import expo.modules.guardianprotection.policy.PolicyManager
import expo.modules.guardianprotection.storage.EncryptedPolicyStore
import expo.modules.guardianprotection.usage.UsageCollector
import java.time.Instant
import java.util.concurrent.ConcurrentHashMap

class GuardianAccessibilityService : AccessibilityService() {
  private lateinit var usage: UsageCollector
  private lateinit var inventory: PackageInventory
  private val lastBlockedAt = ConcurrentHashMap<String, Long>()

  override fun onServiceConnected() {
    super.onServiceConnected()
    running = true
    val manager = PolicyManager(
      EncryptedPolicyStore(this),
      expo.modules.guardianprotection.BuildConfig.GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS,
    )
    manager.start()
    GuardianPolicyRuntime.install(manager)
    usage = UsageCollector(this, EncryptedPolicyStore(this))
    inventory = PackageInventory(this)
  }

  override fun onAccessibilityEvent(event: AccessibilityEvent?) {
    val packageName = event?.packageName?.toString() ?: return
    if (packageName == packageNameOfGuardian()) return
    if (event.eventType != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED &&
      event.eventType != AccessibilityEvent.TYPE_WINDOWS_CHANGED
    ) return
    val collector = usage
    val category = inventory.categoryFor(packageName)
    val snapshot = GuardianPolicyRuntime.hasActiveSnapshot()
    if (!snapshot) return
    runCatching {
      collector.refresh(timezone = null)
      val decision = GuardianPolicyRuntime.evaluateApp(packageName, category, collector.usageToday(packageName, category))
      if (!decision.blocked) return
      val now = System.currentTimeMillis()
      val previous = lastBlockedAt.put(packageName, now)
      if (previous != null && now - previous < BLOCK_DEDUP_MS) return
      GuardianPolicyRuntime.reportAppBlocked(packageName, decision.reasonCode)
      performGlobalAction(GLOBAL_ACTION_BACK)
      startActivity(
        Intent(this, GuardianBlockActivity::class.java)
          .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
          .putExtra(GuardianBlockActivity.EXTRA_APP, packageName)
          .putExtra(GuardianBlockActivity.EXTRA_REASON, decision.reasonCode),
      )
    }
  }

  override fun onInterrupt() = Unit

  override fun onDestroy() {
    running = false
    super.onDestroy()
  }

  private fun packageNameOfGuardian(): String = applicationContext.packageName

  companion object {
    private const val BLOCK_DEDUP_MS = 2_000L
    @Volatile private var running = false

    fun isRunning(): Boolean = running
  }
}
