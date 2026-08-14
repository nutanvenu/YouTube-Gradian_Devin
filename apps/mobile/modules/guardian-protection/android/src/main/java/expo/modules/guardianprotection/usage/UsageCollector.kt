package expo.modules.guardianprotection.usage

import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import expo.modules.guardianprotection.inventory.PackageInventory
import expo.modules.guardianprotection.storage.EncryptedPolicyStore
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime

class UsageCollector(
  private val context: Context,
  private val store: EncryptedPolicyStore,
  private val inventory: PackageInventory = PackageInventory(context),
) {
  @Synchronized
  fun refresh(now: Instant = Instant.now(), timezone: String? = null): UsageCollection {
    val zone = ZoneId.of(timezone ?: ZoneId.systemDefault().id)
    val localNow = now.atZone(zone)
    val dayStart = localNow.toLocalDate().atStartOfDay(zone).toInstant()
    val events = query(dayStart, now)
    val slices = UsageSessionDeriver.derive(events, dayStart, now, zone)
    val appTotals = slices.groupBy { it.packageName }.mapValues { (_, values) -> values.sumOf { it.durationMs } }
    val categoryTotals = appTotals.entries.groupBy { inventory.categoryFor(it.key) }
      .mapValues { (_, values) -> values.sumOf { it.value } }
    val totals = buildMap {
      appTotals.forEach { (app, value) -> put("APP:$app", value / 1000) }
      categoryTotals.forEach { (category, value) -> put("CATEGORY:$category", value / 1000) }
      put("DEVICE", appTotals.values.sum() / 1000)
    }
    store.mergeUsageSnapshot(localNow.toLocalDate().toString(), totals)
    return UsageCollection(
      date = localNow.toLocalDate().toString(),
      appMillis = appTotals,
      categoryMillis = categoryTotals,
      deviceMillis = appTotals.values.sum(),
    )
  }

  fun usageToday(packageName: String?, category: String?, timezone: String? = null): UsageContext {
    val zone = ZoneId.of(timezone ?: ZoneId.systemDefault().id)
    val date = ZonedDateTime.now(zone).toLocalDate().toString()
    val values = store.usageSnapshots()[date].orEmpty()
    return UsageContext(
      appMillis = packageName?.let { (values["APP:$it"] ?: 0L) * 1000 } ?: 0L,
      categoryMillis = category?.let { (values["CATEGORY:$it"] ?: 0L) * 1000 } ?: 0L,
      deviceMillis = (values["DEVICE"] ?: 0L) * 1000,
    )
  }

  fun summary(range: Map<String, Any?>): Map<String, Any?> {
    val start = (range["start"] as? String)?.let { runCatching { Instant.parse(it) }.getOrNull() }
    val end = (range["end"] as? String)?.let { runCatching { Instant.parse(it) }.getOrNull() }
    val snapshots = store.usageSnapshots().filterKeys { date ->
      val day = runCatching { LocalDate.parse(date).atStartOfDay(ZoneId.of("UTC")).toInstant() }.getOrNull()
      (start == null || day == null || !day.isBefore(start)) && (end == null || day == null || day.isBefore(end))
    }
    val byTarget = snapshots.values
      .flatMap { it.entries }
      .groupBy({ it.key }, { it.value })
      .mapValues { (_, values) -> values.sum() }
    return mapOf(
      "range" to range,
      "totalSeconds" to byTarget.values.sum(),
      "byTarget" to byTarget,
    )
  }

  private fun query(begin: Instant, end: Instant): List<UsageEvent> {
    val manager = context.getSystemService(UsageStatsManager::class.java)
    val stream = manager.queryEvents(begin.toEpochMilli(), end.toEpochMilli()) ?: return emptyList()
    val raw = UsageEvents.Event()
    val events = mutableListOf<UsageEvent>()
    while (stream.hasNextEvent()) {
      stream.getNextEvent(raw)
      val type = when (raw.eventType) {
        UsageEvents.Event.ACTIVITY_RESUMED,
        UsageEvents.Event.MOVE_TO_FOREGROUND -> UsageEventType.RESUMED
        UsageEvents.Event.ACTIVITY_PAUSED,
        UsageEvents.Event.ACTIVITY_STOPPED,
        UsageEvents.Event.MOVE_TO_BACKGROUND -> UsageEventType.PAUSED
        else -> null
      }
      if (type != null && !raw.packageName.isNullOrBlank()) {
        events += UsageEvent(raw.packageName, Instant.ofEpochMilli(raw.timeStamp), type)
      }
    }
    return events
  }
}

data class UsageCollection(
  val date: String,
  val appMillis: Map<String, Long>,
  val categoryMillis: Map<String, Long>,
  val deviceMillis: Long,
)

data class UsageContext(
  val appMillis: Long,
  val categoryMillis: Long,
  val deviceMillis: Long,
)
