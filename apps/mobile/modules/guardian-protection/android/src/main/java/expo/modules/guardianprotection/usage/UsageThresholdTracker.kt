package expo.modules.guardianprotection.usage

class UsageThresholdTracker(private val warningMinutes: Long = 5) {
  private val warned = mutableSetOf<String>()
  private val expired = mutableSetOf<String>()

  @Synchronized
  fun update(targetRef: String, usedMs: Long, limitMs: Long): UsageThresholdEvent {
    if (limitMs <= 0 || usedMs < 0) return UsageThresholdEvent.NONE
    if (usedMs >= limitMs) {
      if (expired.add(targetRef)) return UsageThresholdEvent.EXPIRED
      return UsageThresholdEvent.NONE
    }
    val warningAt = (limitMs - warningMinutes * 60_000).coerceAtLeast(0)
    if (usedMs >= warningAt && warned.add(targetRef)) return UsageThresholdEvent.WARNING
    return UsageThresholdEvent.NONE
  }

  @Synchronized
  fun reset(targetRef: String) {
    warned.remove(targetRef)
    expired.remove(targetRef)
  }

  @Synchronized
  fun clear() {
    warned.clear()
    expired.clear()
  }
}

enum class UsageThresholdEvent {
  NONE,
  WARNING,
  EXPIRED,
}
