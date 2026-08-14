package expo.modules.guardianprotection.inventory

import org.junit.Assert.assertEquals
import org.junit.Test

class AppInventoryTest {
  @Test
  fun newlyObservedPackagesRemainPendingUntilReviewed() {
    val detector = NewAppDetector()
    assertEquals(listOf("com.one", "com.two"), detector.newPackages(listOf("com.one", "com.two")))
    assertEquals(listOf("com.one", "com.two", "com.three"), detector.newPackages(listOf("com.one", "com.two", "com.three")))
    detector.markReviewed("com.one")
    assertEquals(listOf("com.two", "com.three"), detector.newPackages(listOf("com.one", "com.two", "com.three")))
  }
}
