package expo.modules.guardianprotection.accessibility

import expo.modules.guardianprotection.accessibility.BudgetEnforcementController.TickerAction
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BudgetEnforcementControllerTest {
  @Test
  fun startsOnlyForBudgetedNonGuardianForegroundAndStopsOnPackageChange() {
    val controller = BudgetEnforcementController()

    assertTrue(
      controller.updateForeground("com.example.budgeted", hasBudget = true, guardianPackage = "com.guardian")
        == TickerAction.START,
    )
    assertTrue(controller.isTickerActiveFor("com.example.budgeted"))
    assertTrue(controller.isCurrentForeground("com.example.budgeted"))
    assertTrue(
      controller.updateForeground("com.example.unbudgeted", hasBudget = false, guardianPackage = "com.guardian")
        == TickerAction.STOP,
    )
    assertFalse(controller.isTickerActiveFor("com.example.budgeted"))
    assertTrue(controller.isCurrentForeground("com.example.unbudgeted"))
    assertTrue(
      controller.updateForeground("com.guardian", hasBudget = true, guardianPackage = "com.guardian")
        == TickerAction.STOP,
    )
    assertFalse(controller.isTickerActiveFor("com.guardian"))
  }

  @Test
  fun repeatedExhaustionReportsOnlyOnceWithinExistingDedupWindow() {
    val controller = BudgetEnforcementController(blockDedupMs = 2_000L)

    assertTrue(controller.shouldReportBlock("com.example.budgeted", 10_000L))
    assertFalse(controller.shouldReportBlock("com.example.budgeted", 11_000L))
    assertTrue(controller.shouldReportBlock("com.example.budgeted", 12_000L))
  }
}
