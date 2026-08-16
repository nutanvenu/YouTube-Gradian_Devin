package expo.modules.guardianprotection.inventory

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class InventoryObservationTest {
  @Test
  fun coverageIsAlwaysExplicitlyPartialAndListsOnlyObservedSources() {
    val sources = setOf(InventorySource.LAUNCHER, InventorySource.USAGE_STATS)

    assertEquals("PARTIAL", InventoryCoverage.PARTIAL)
    assertEquals(listOf("LAUNCHER", "USAGE_STATS"), InventoryCoverage.sourceLabels(sources))
    assertTrue(InventoryCoverage.detail(sources).contains("incomplete"))
  }
}
