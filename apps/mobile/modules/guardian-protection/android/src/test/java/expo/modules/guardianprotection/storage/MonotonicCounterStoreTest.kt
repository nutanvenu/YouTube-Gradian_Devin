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

  @Test
  fun restoredCounterNeverMovesBackwards() {
    val counter = MonotonicCounterStore()
    counter.restore(50, 500)
    counter.restore(40, 400)
    assertEquals(50, counter.total())
    assertEquals(55, counter.add(5, 500))
  }

  @Test(expected = IllegalArgumentException::class)
  fun negativeDeltaIsRejected() {
    MonotonicCounterStore().add(-1, 1)
  }
}
