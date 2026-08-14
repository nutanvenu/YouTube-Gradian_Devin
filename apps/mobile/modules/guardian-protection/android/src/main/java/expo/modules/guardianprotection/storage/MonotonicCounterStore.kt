package expo.modules.guardianprotection.storage

import kotlin.math.max

class MonotonicCounterStore {
  private var total: Long = 0
  private var lastElapsedRealtime: Long = 0

  @Synchronized
  fun add(delta: Long, elapsedRealtime: Long): Long {
    require(delta >= 0) { "Counter deltas cannot be negative" }
    require(elapsedRealtime >= lastElapsedRealtime) { "Elapsed realtime cannot move backwards" }
    total = Math.addExact(total, delta)
    lastElapsedRealtime = elapsedRealtime
    return total
  }

  @Synchronized
  fun restore(total: Long, elapsedRealtime: Long) {
    require(total >= 0 && elapsedRealtime >= 0)
    this.total = max(this.total, total)
    this.lastElapsedRealtime = max(this.lastElapsedRealtime, elapsedRealtime)
  }

  fun total(): Long = total
}
