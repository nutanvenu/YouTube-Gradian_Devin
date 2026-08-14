package expo.modules.guardianprotection.usage

import org.junit.Assert.assertEquals
import org.junit.Test

class UsageThresholdTest {
  @Test
  fun emitsWarningOnceBeforeExpiryAndExpiryAtLimit() {
    val tracker = UsageThresholdTracker(warningMinutes = 5)
    assertEquals(UsageThresholdEvent.NONE, tracker.update("app", 0, 600_000))
    assertEquals(UsageThresholdEvent.WARNING, tracker.update("app", 300_000, 600_000))
    assertEquals(UsageThresholdEvent.NONE, tracker.update("app", 301_000, 600_000))
    assertEquals(UsageThresholdEvent.EXPIRED, tracker.update("app", 600_000, 600_000))
    assertEquals(UsageThresholdEvent.NONE, tracker.update("app", 610_000, 600_000))
  }
}
