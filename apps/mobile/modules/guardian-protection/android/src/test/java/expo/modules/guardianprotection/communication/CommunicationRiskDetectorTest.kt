package expo.modules.guardianprotection.communication

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CommunicationRiskDetectorTest {
  @Test
  fun `detector emits minimized deterministic signals without content`() {
    val signal = CommunicationRiskDetector.classify(
      "Urgent message",
      "I am worried they may threaten me",
    )

    requireNotNull(signal)
    assertEquals("HARASSMENT", signal.category)
    assertEquals("MEDIUM", signal.severity)
    assertEquals("RULE_HARASSMENT_TERM", signal.reasonCode)
    check(signal.toString().contains("threat", ignoreCase = true).not())
  }

  @Test
  fun `unknown content produces no risk event`() {
    assertNull(CommunicationRiskDetector.classify("Dinner plans", "See you at seven"))
  }

  @Test
  fun `labelled fixture reports rules precision recall and runtime`() {
    data class Fixture(val title: String, val body: String, val expected: String?)
    val fixtures = listOf(
      Fixture("Check in", "See you soon", null),
      Fixture("Concern", "They may threaten me", "HARASSMENT"),
      Fixture("Safety", "I want to kill myself", "SELF_HARM"),
      Fixture("Photo", "Please send nudes", "SEXUAL_CONTENT"),
      Fixture("School", "The homework is due", null),
      Fixture("Threat", "I will dox you", "HARASSMENT"),
      Fixture("Support", "I need help", null),
      Fixture("Explicit", "This is sexual assault", "SEXUAL_CONTENT"),
    )
    val started = System.nanoTime()
    val predictions = fixtures.map { CommunicationRiskDetector.classify(it.title, it.body)?.category }
    val elapsedNanos = System.nanoTime() - started
    val truePositives = fixtures.indices.count { fixtures[it].expected != null && predictions[it] == fixtures[it].expected }
    val falsePositives = fixtures.indices.count { fixtures[it].expected == null && predictions[it] != null }
    val falseNegatives = fixtures.indices.count { fixtures[it].expected != null && predictions[it] == null }
    val precision = truePositives.toDouble() / (truePositives + falsePositives)
    val recall = truePositives.toDouble() / (truePositives + falseNegatives)
    println("COMMUNICATION_RULES_MEASUREMENT fixtures=${fixtures.size} precision=$precision recall=$recall runtimeNanos=$elapsedNanos")
    assertEquals(1.0, precision, 0.0)
    assertEquals(1.0, recall, 0.0)
  }
}
