package expo.modules.guardianprotection.accessibility

import android.accessibilityservice.AccessibilityService
import android.os.Handler
import android.os.Looper
import android.view.accessibility.AccessibilityEvent
import android.content.Intent
import expo.modules.guardianprotection.inventory.PackageInventory
import expo.modules.guardianprotection.policy.GuardianPolicyRuntime
import expo.modules.guardianprotection.policy.PolicyManager
import expo.modules.guardianprotection.storage.EncryptedPolicyStore
import expo.modules.guardianprotection.usage.UsageCollector

class GuardianAccessibilityService : AccessibilityService() {
  private lateinit var usage: UsageCollector
  private lateinit var inventory: PackageInventory
  private val enforcement = BudgetEnforcementController()
  private val mainHandler = Handler(Looper.getMainLooper())
  private var foregroundPackage: String? = null
  private var foregroundCategory: String? = null
  private val budgetTicker = object : Runnable {
    override fun run() {
      val packageName = foregroundPackage ?: return
      if (!enforcement.isTickerActiveFor(packageName) ||
        !GuardianPolicyRuntime.hasActiveSnapshot()
      ) {
        stopBudgetTicker()
        return
      }
      evaluateForeground(packageName, foregroundCategory ?: inventory.categoryFor(packageName))
      if (enforcement.isTickerActiveFor(packageName)) {
        mainHandler.postDelayed(this, BUDGET_TICK_INTERVAL_MS)
      }
    }
  }

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
    if (event.eventType != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED &&
      event.eventType != AccessibilityEvent.TYPE_WINDOWS_CHANGED
    ) return
    updateForeground(packageName)
    if (packageName == packageNameOfGuardian()) return
    evaluateForeground(packageName, foregroundCategory ?: inventory.categoryFor(packageName))
  }

  private fun updateForeground(packageName: String) {
    val category = if (packageName == packageNameOfGuardian()) null else inventory.categoryFor(packageName)
    foregroundPackage = packageName
    foregroundCategory = category
    val hasBudget = GuardianPolicyRuntime.hasActiveSnapshot() &&
      GuardianPolicyRuntime.hasApplicableAppBudget(packageName, category)
    when (enforcement.updateForeground(packageName, hasBudget, packageNameOfGuardian())) {
      BudgetEnforcementController.TickerAction.START -> {
        mainHandler.removeCallbacks(budgetTicker)
        mainHandler.postDelayed(budgetTicker, BUDGET_TICK_INTERVAL_MS)
      }
      BudgetEnforcementController.TickerAction.STOP -> stopBudgetTicker()
      BudgetEnforcementController.TickerAction.NONE -> Unit
    }
  }

  private fun evaluateForeground(packageName: String, category: String?) {
    val collector = usage
    runCatching {
      collector.refresh(timezone = null)
      val decision = GuardianPolicyRuntime.evaluateApp(packageName, category, collector.usageToday(packageName, category))
      if (!decision.blocked) return
      stopBudgetTicker()
      val now = System.currentTimeMillis()
      if (!enforcement.shouldReportBlock(packageName, now)) return
      GuardianPolicyRuntime.reportAppBlocked(packageName, decision.reasonCode)
      performGlobalAction(GLOBAL_ACTION_BACK)
      mainHandler.postDelayed({
        startActivity(
          Intent(this, GuardianBlockActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            .putExtra(GuardianBlockActivity.EXTRA_APP, packageName)
            .putExtra(GuardianBlockActivity.EXTRA_REASON, decision.reasonCode),
        )
      }, BLOCK_SURFACE_DELAY_MS)
    }
  }

  override fun onInterrupt() = Unit

  override fun onDestroy() {
    stopBudgetTicker()
    running = false
    super.onDestroy()
  }

  private fun stopBudgetTicker() {
    mainHandler.removeCallbacks(budgetTicker)
    enforcement.cancel()
  }

  private fun packageNameOfGuardian(): String = applicationContext.packageName

  companion object {
    private const val BUDGET_TICK_INTERVAL_MS = 3_000L
    private const val BLOCK_SURFACE_DELAY_MS = 300L
    @Volatile private var running = false

    fun isRunning(): Boolean = running
  }
}
