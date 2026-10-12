package expo.modules.guardianprotection.accessibility

import org.junit.Assert.assertEquals
import org.junit.Test

class AppBlockExplanationTest {
  @Test
  fun explicitBlocksDoNotClaimThatTimeHasExpired() {
    for (reason in listOf("EXPLICIT_TARGET_RULE", "TEMPORARY_PARENT_OVERRIDE")) {
      assertEquals(
        "Your parent has blocked this app. Ask a parent to change the app rule if you need access.",
        appBlockExplanation(reason),
      )
    }
  }

  @Test
  fun exhaustedBudgetsExplainTheTimeLimit() {
    for (reason in listOf("BUDGET_EXHAUSTED", "DEVICE_BUDGET_EXHAUSTED", "UNKNOWN_APP_BUDGET_EXHAUSTED")) {
      assertEquals("Your time limit has been reached. Ask a parent for more time.", appBlockExplanation(reason))
    }
  }

  @Test
  fun routinesExplainTheSchedule() {
    for (reason in listOf("MANUAL_ROUTINE", "SCHEDULED_ROUTINE", "SCHEDULE_OUTSIDE_WINDOW")) {
      assertEquals(
        "Your current routine or schedule blocks this app. Ask a parent to review the routine or schedule.",
        appBlockExplanation(reason),
      )
    }
  }

  @Test
  fun parentApprovalHasItsOwnExplanation() {
    assertEquals("This app needs a parent's approval. Ask a parent before using it.", appBlockExplanation("REQUIRES_PARENT_APPROVAL"))
  }

  @Test
  fun missingAndUnknownReasonsDoNotInventAnExpiredLimit() {
    for (reason in listOf(null, "EXPLICIT_CATEGORY_RULE", "AGE_BAND_HARD_CATEGORY", "NEW_REASON")) {
      assertEquals(
        "Guardian's rules block this app. Ask a parent to review the rules if you need access.",
        appBlockExplanation(reason),
      )
    }
  }
}
