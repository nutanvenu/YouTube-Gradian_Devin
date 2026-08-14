package expo.modules.guardianprotection.usage

import java.time.Instant
import java.time.ZoneId
import java.time.temporal.ChronoUnit

enum class UsageEventType {
  RESUMED,
  PAUSED,
  STOPPED,
}

data class UsageEvent(
  val packageName: String,
  val timestamp: Instant,
  val type: UsageEventType,
)

data class UsageSlice(
  val packageName: String,
  val localDate: String,
  val durationMs: Long,
)

object UsageSessionDeriver {
  fun derive(
    events: List<UsageEvent>,
    rangeStart: Instant,
    rangeEnd: Instant,
    zone: ZoneId,
  ): List<UsageSlice> {
    require(!rangeEnd.isBefore(rangeStart)) { "Usage range must be ordered" }
    var activePackage: String? = null
    var activeSince: Instant? = null
    val slices = mutableListOf<UsageSlice>()

    fun close(at: Instant) {
      val packageName = activePackage
      val since = activeSince
      if (packageName != null && since != null) {
        appendSplit(slices, packageName, since.coerceAtLeast(rangeStart), at.coerceAtMost(rangeEnd), zone)
      }
      activePackage = null
      activeSince = null
    }

    events
      .asSequence()
      .filter { !it.timestamp.isBefore(rangeStart) && !it.timestamp.isAfter(rangeEnd) }
      .sortedBy { it.timestamp }
      .forEach { event ->
        when (event.type) {
          UsageEventType.RESUMED -> {
            if (activePackage != event.packageName) close(event.timestamp)
            if (activePackage == null) {
              activePackage = event.packageName
              activeSince = event.timestamp
            }
          }
          UsageEventType.PAUSED, UsageEventType.STOPPED -> {
            if (activePackage == event.packageName) close(event.timestamp)
          }
        }
      }
    close(rangeEnd)
    return slices
  }

  private fun appendSplit(
    output: MutableList<UsageSlice>,
    packageName: String,
    start: Instant,
    end: Instant,
    zone: ZoneId,
  ) {
    if (!end.isAfter(start)) return
    var cursor = start
    while (cursor.isBefore(end)) {
      val local = cursor.atZone(zone)
      val nextMidnight = local.toLocalDate().plusDays(1).atStartOfDay(zone).toInstant()
      val segmentEnd = minOf(end, nextMidnight)
      val duration = ChronoUnit.MILLIS.between(cursor, segmentEnd)
      if (duration > 0) {
        val date = local.toLocalDate().toString()
        val previous = output.indexOfLast { it.packageName == packageName && it.localDate == date }
        if (previous >= 0) {
          val old = output[previous]
          output[previous] = old.copy(durationMs = old.durationMs + duration)
        } else {
          output += UsageSlice(packageName, date, duration)
        }
      }
      cursor = segmentEnd
    }
  }

  private fun Instant.coerceAtLeast(other: Instant): Instant = if (isBefore(other)) other else this
  private fun Instant.coerceAtMost(other: Instant): Instant = if (isAfter(other)) other else this
}
