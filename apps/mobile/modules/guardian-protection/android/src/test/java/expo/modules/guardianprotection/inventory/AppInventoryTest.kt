package expo.modules.guardianprotection.inventory

import org.junit.Assert.assertEquals
import org.junit.Test

class AppInventoryTest {
  @Test
  fun newlyObservedPackagesAreReportedOnce() {
    val detector = NewAppDetector()
    assertEquals(listOf("com.one", "com.two"), detector.newPackages(listOf("com.one", "com.two")))
    assertEquals(listOf("com.three"), detector.newPackages(listOf("com.one", "com.three")))
  }
}
