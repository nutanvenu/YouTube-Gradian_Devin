package expo.modules.guardianprotection.observability

import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference

object GuardianPerformanceMetrics {
  private val vpnDecisionCount = AtomicLong()
  private val vpnDecisionNanos = AtomicLong()
  private val policyApplyCount = AtomicLong()
  private val policyApplyNanos = AtomicLong()
  private val usageRefreshCount = AtomicLong()
  private val usageRefreshNanos = AtomicLong()
  private val bridgeEventCount = AtomicLong()
  private val startupMillis = AtomicReference<Long?>(null)

  fun recordVpnDecision(durationNanos: Long) {
    vpnDecisionCount.incrementAndGet()
    vpnDecisionNanos.addAndGet(durationNanos)
  }

  fun recordPolicyApply(durationNanos: Long) {
    policyApplyCount.incrementAndGet()
    policyApplyNanos.addAndGet(durationNanos)
  }

  fun recordUsageRefresh(durationNanos: Long) {
    usageRefreshCount.incrementAndGet()
    usageRefreshNanos.addAndGet(durationNanos)
  }

  fun recordBridgeEvent() {
    bridgeEventCount.incrementAndGet()
  }

  fun recordStartup(durationMillis: Long) {
    startupMillis.compareAndSet(null, durationMillis)
  }

  fun snapshot(): Map<String, Any?> {
    fun average(total: Long, count: Long): Long = if (count == 0L) 0L else total / count
    val decisions = vpnDecisionCount.get()
    val policyApplies = policyApplyCount.get()
    val usageRefreshes = usageRefreshCount.get()
    return mapOf(
      "vpnDecisionCount" to decisions,
      "vpnDecisionAverageMicros" to average(vpnDecisionNanos.get(), decisions) / 1_000,
      "policyApplyCount" to policyApplies,
      "policyApplyAverageMillis" to average(policyApplyNanos.get(), policyApplies) / 1_000_000,
      "usageRefreshCount" to usageRefreshes,
      "usageRefreshAverageMillis" to average(usageRefreshNanos.get(), usageRefreshes) / 1_000_000,
      "bridgeEventCount" to bridgeEventCount.get(),
      "moduleStartupMillis" to startupMillis.get(),
      "batteryMeasurement" to "UNAVAILABLE_FROM_EMULATOR",
    )
  }
}
