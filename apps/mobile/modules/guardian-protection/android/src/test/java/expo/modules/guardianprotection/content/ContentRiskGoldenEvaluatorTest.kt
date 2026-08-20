package expo.modules.guardianprotection.content

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ContentRiskGoldenEvaluatorTest {
  @Test
  fun `golden dataset reports metrics and does not regress frozen rules baseline`() {
    val report = ContentRiskGoldenEvaluator.evaluate()
    println(report.render())
    ContentRiskGoldenEvaluator.assertNotWorseThanBaseline(report)
    assertTrue(report.totalCases >= 100)
    assertTrue(report.current.values.all { it.falseNegatives == 0 })
  }

  @Test
  fun `inaccessible custom rendered cases are excluded from accuracy claims`() {
    val report = ContentRiskGoldenEvaluator.evaluate()
    assertEquals(10, report.unavailableCases)
    assertEquals(130, report.evaluatedCases)
  }
}
