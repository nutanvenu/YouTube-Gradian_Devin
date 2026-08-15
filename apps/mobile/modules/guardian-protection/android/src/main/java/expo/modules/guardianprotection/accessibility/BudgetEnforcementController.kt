package expo.modules.guardianprotection.accessibility

class BudgetEnforcementController(
  private val blockDedupMs: Long = DEFAULT_BLOCK_DEDUP_MS,
) {
  private var foregroundPackage: String? = null
  private var tickerActive = false
  private val lastBlockedAt = mutableMapOf<String, Long>()

  @Synchronized
  fun updateForeground(
    packageName: String,
    hasBudget: Boolean,
    guardianPackage: String,
  ): TickerAction {
    val shouldRun = packageName != guardianPackage && hasBudget
    val action = when {
      shouldRun && (!tickerActive || foregroundPackage != packageName) -> TickerAction.START
      !shouldRun && (tickerActive || foregroundPackage != packageName) -> TickerAction.STOP
      else -> TickerAction.NONE
    }
    foregroundPackage = packageName
    tickerActive = shouldRun
    return action
  }

  @Synchronized
  fun cancel(): Boolean {
    val wasActive = tickerActive
    tickerActive = false
    return wasActive
  }

  @Synchronized
  fun isTickerActiveFor(packageName: String): Boolean =
    tickerActive && foregroundPackage == packageName

  @Synchronized
  fun isCurrentForeground(packageName: String): Boolean =
    foregroundPackage == packageName

  @Synchronized
  fun shouldReportBlock(packageName: String, nowMillis: Long): Boolean {
    val previous = lastBlockedAt[packageName]
    if (previous != null && nowMillis - previous < blockDedupMs) return false
    lastBlockedAt[packageName] = nowMillis
    return true
  }

  enum class TickerAction {
    START,
    STOP,
    NONE,
  }

  private companion object {
    const val DEFAULT_BLOCK_DEDUP_MS = 2_000L
  }
}
