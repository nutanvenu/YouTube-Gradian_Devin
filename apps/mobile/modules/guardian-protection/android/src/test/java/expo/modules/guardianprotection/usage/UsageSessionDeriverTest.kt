package expo.modules.guardianprotection.usage

import java.time.Instant
import java.time.ZoneId
import org.junit.Assert.assertEquals
import org.junit.Test

class UsageSessionDeriverTest {
  @Test
  fun derivesAndSplitsForegroundSessionAcrossMidnight() {
    val start = Instant.parse("2026-03-08T23:59:30Z")
    val end = Instant.parse("2026-03-09T00:01:30Z")
    val slices = UsageSessionDeriver.derive(
      events = listOf(
        UsageEvent("com.example.app", start, UsageEventType.RESUMED),
        UsageEvent("com.example.app", end, UsageEventType.PAUSED),
      ),
      rangeStart = start,
      rangeEnd = end,
      zone = ZoneId.of("UTC"),
    )

    assertEquals(
      listOf(
        UsageSlice("com.example.app", "2026-03-08", 30_000),
        UsageSlice("com.example.app", "2026-03-09", 90_000),
      ),
      slices,
    )
  }

  @Test
  fun closesPreviousAppWhenAnotherAppResumes() {
    val start = Instant.parse("2026-01-01T10:00:00Z")
    val middle = Instant.parse("2026-01-01T10:05:00Z")
    val end = Instant.parse("2026-01-01T10:07:00Z")
    val slices = UsageSessionDeriver.derive(
      events = listOf(
        UsageEvent("com.one", start, UsageEventType.RESUMED),
        UsageEvent("com.two", middle, UsageEventType.RESUMED),
      ),
      rangeStart = start,
      rangeEnd = end,
      zone = ZoneId.of("UTC"),
    )

    assertEquals(300_000, slices.first { it.packageName == "com.one" }.durationMs)
    assertEquals(120_000, slices.first { it.packageName == "com.two" }.durationMs)
  }
}
