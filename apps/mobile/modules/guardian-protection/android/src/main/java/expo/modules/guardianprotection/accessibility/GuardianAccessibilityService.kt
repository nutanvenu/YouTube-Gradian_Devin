package expo.modules.guardianprotection.accessibility

import android.accessibilityservice.AccessibilityService
import android.os.Handler
import android.os.HandlerThread
import android.os.Looper
import android.os.Process
import android.util.Log
import expo.modules.guardianprotection.BuildConfig
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
  private val budgetThread = HandlerThread(
    "GuardianBudgetEvaluator",
    Process.THREAD_PRIORITY_BACKGROUND,
  )
  private lateinit var budgetHandler: Handler
  @Volatile private var foregroundPackage: String? = null
  @Volatile private var foregroundCategory: String? = null
  @Volatile private var serviceDestroyed = false
  private val budgetTicker = object : Runnable {
    override fun run() {
      val packageName = foregroundPackage ?: return
      if (BuildConfig.DEBUG) Log.d("GuardianBudget", "budget_tick")
      if (!enforcement.isTickerActiveFor(packageName) ||
        !GuardianPolicyRuntime.hasActiveSnapshot() ||
        serviceDestroyed
      ) {
        stopBudgetTicker()
        return
      }
      evaluateForeground(packageName, foregroundCategory ?: inventory.categoryFor(packageName))
      if (enforcement.isTickerActiveFor(packageName)) {
        budgetHandler.postDelayed(this, BUDGET_TICK_INTERVAL_MS)
      }
    }
  }

  override fun onServiceConnected() {
    super.onServiceConnected()
    serviceDestroyed = false
    if (!budgetThread.isAlive) budgetThread.start()
    if (!::budgetHandler.isInitialized) budgetHandler = Handler(budgetThread.looper)
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
    val category = foregroundCategory ?: inventory.categoryFor(packageName)
    budgetHandler.post {
      evaluateForeground(packageName, category)
    }
  }

  private fun updateForeground(packageName: String) {
    val category = if (packageName == packageNameOfGuardian()) null else inventory.categoryFor(packageName)
    foregroundPackage = packageName
    foregroundCategory = category
    val hasBudget = GuardianPolicyRuntime.hasActiveSnapshot() &&
      GuardianPolicyRuntime.hasApplicableAppBudget(packageName, category)
    when (enforcement.updateForeground(packageName, hasBudget, packageNameOfGuardian())) {
      BudgetEnforcementController.TickerAction.START -> {
        budgetHandler.removeCallbacks(budgetTicker)
        budgetHandler.postDelayed(budgetTicker, BUDGET_TICK_INTERVAL_MS)
      }
      BudgetEnforcementController.TickerAction.STOP -> stopBudgetTicker()
      BudgetEnforcementController.TickerAction.NONE -> Unit
    }
  }

  private fun evaluateForeground(packageName: String, category: String?) {
    if (serviceDestroyed || !enforcement.isCurrentForeground(packageName)) return
    val collector = usage
    runCatching {
      collector.refresh(timezone = null)
      if (serviceDestroyed || !enforcement.isCurrentForeground(packageName)) return@runCatching
      val decision = GuardianPolicyRuntime.evaluateApp(packageName, category, collector.usageToday(packageName, category))
      if (!decision.blocked) return
      stopBudgetTicker()
      val now = System.currentTimeMillis()
      if (!enforcement.shouldReportBlock(packageName, now)) return
      GuardianPolicyRuntime.reportAppBlocked(packageName, decision.reasonCode)
      mainHandler.post {
        if (serviceDestroyed) return@post
        performGlobalAction(GLOBAL_ACTION_BACK)
        mainHandler.postDelayed({
          if (serviceDestroyed) return@postDelayed
          startActivity(
            Intent(this, GuardianBlockActivity::class.java)
              .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
              .putExtra(GuardianBlockActivity.EXTRA_APP, packageName)
              .putExtra(GuardianBlockActivity.EXTRA_REASON, decision.reasonCode),
          )
        }, BLOCK_SURFACE_DELAY_MS)
      }
    }
  }

  override fun onInterrupt() = Unit

  override fun onDestroy() {
    serviceDestroyed = true
    stopBudgetTicker()
    if (budgetThread.isAlive) budgetThread.quitSafely()
    running = false
    super.onDestroy()
  }

  private fun stopBudgetTicker() {
    if (::budgetHandler.isInitialized) budgetHandler.removeCallbacks(budgetTicker)
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
