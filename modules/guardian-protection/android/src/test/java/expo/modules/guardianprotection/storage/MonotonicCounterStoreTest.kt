package expo.modules.guardianprotection.storage

import org.junit.Assert.assertEquals
import org.junit.Test

class MonotonicCounterStoreTest {
  @Test
  fun counterSurvivesWallClockRollbackByUsingElapsedRealtime() {
    val counter = MonotonicCounterStore()
    assertEquals(10, counter.add(10, 100))
    assertEquals(15, counter.add(5, 90 + 20))
    assertEquals(15, counter.total())
  }
}
