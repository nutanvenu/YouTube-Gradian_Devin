package expo.modules.guardianprotection.communication

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CommunicationRiskDetectorTest {
  @Test
  fun `detector emits minimized deterministic signals without content`() {
    val signal = CommunicationRiskDetector.classify(
      "Urgent message",
      "They said they will hurt you and keep threatening you",
    )

    requireNotNull(signal)
    assertEquals("HARASSMENT", signal.category)
    assertEquals("MEDIUM", signal.severity)
    assertEquals("HARASSMENT_THREAT+HARASSMENT_TARGET", signal.reasonCode)
    check(signal.confidence >= 0.75)
    check(signal.toString().contains("They said", ignoreCase = true).not())
  }

  @Test
  fun `unknown content produces no risk event`() {
    assertNull(CommunicationRiskDetector.classify("Dinner plans", "See you at seven"))
    assertNull(CommunicationRiskDetector.classify("suicide", "A song lyric", CommunicationNotificationContext("com.whatsapp", "msg", "chat")))
  }

  @Test
  fun `categories require multiple contextual signals`() {
    assertEquals("GROOMING", requireNotNull(CommunicationRiskDetector.classify(
      "Please keep this secret",
      "How old are you? Meet me alone",
    )).category)
    assertEquals("PHISHING_CREDENTIAL_THEFT", requireNotNull(CommunicationRiskDetector.classify(
      "Urgent action required",
      "Your account is suspended, click here and send me your verification code",
    )).category)
    assertEquals("SEXUAL_SOLICITATION", requireNotNull(CommunicationRiskDetector.classify(
      "Please share an intimate picture",
      "Show me that picture privately",
    )).category)
  }

  @Test
  fun `runtime scopes communication apps and throttles duplicate notifications`() {
    val emitted = mutableListOf<String>()
    CommunicationSafetyRuntime.setEnabled(true)
    CommunicationSafetyRuntime.setListener { _, packageName -> emitted.add(packageName) }
    CommunicationSafetyRuntime.processNotification(
      "com.android.systemui",
      "Urgent",
      "Your login is suspended, click here and send your password",
      "msg",
      "chat",
      1_000L,
    )
    CommunicationSafetyRuntime.processNotification(
      "com.whatsapp",
      "Urgent",
      "Your login is suspended, click here and send your password",
      "msg",
      "chat",
      2_000L,
    )
    CommunicationSafetyRuntime.processNotification(
      "com.whatsapp",
      "Urgent",
      "Your login is suspended, click here and send your password",
      "msg",
      "chat",
      3_000L,
    )
    assertEquals(listOf("com.whatsapp"), emitted)
    CommunicationSafetyRuntime.setListener(null)
    CommunicationSafetyRuntime.setEnabled(false)
  }

  @Test
  fun `labelled fixture reports per category precision recall runtime and battery limitation`() {
    data class Fixture(val title: String, val body: String, val expected: String?)
    val fixtures = listOf(
      Fixture("I need help", "Can we talk after school?", null),
      Fixture("Homework", "The homework problem asks about suicide rates in history.", null),
      Fixture("News", "News headline: new safety rules announced today.", null),
      Fixture("Lyrics", "The song says 'kill myself' in the chorus.", null),
      Fixture("Medical", "The doctor discussed self-harm warning signs.", null),
      Fixture("One word", "nudes", null),
      Fixture("Dinner", "Send me the recipe photo.", null),
      Fixture("Class", "We should meet in the library tomorrow.", null),
      Fixture("Sports", "The team captain will threaten the record.", null),
      Fixture("Bank lesson", "Our homework covers password security.", null),
      Fixture("Self harm", "I am going to kill myself tonight.", "SELF_HARM"),
      Fixture("Self harm", "I plan to end my life and there is no reason to live.", "SELF_HARM"),
      Fixture("Sexual", "Please send explicit photos and nudes.", "SEXUAL_CONTENT"),
      Fixture("Sexual", "Share a nude picture with me.", "SEXUAL_SOLICITATION"),
      Fixture("Sexual", "This contains explicit sexual assault material.", "SEXUAL_CONTENT"),
      Fixture("Solicitation", "Please share an intimate picture.", "SEXUAL_SOLICITATION"),
      Fixture("Grooming", "Keep this secret, how old are you?", "GROOMING"),
      Fixture("Grooming", "Don't tell anyone; meet me alone, are you underage?", "GROOMING"),
      Fixture("Harassment", "I will hurt you and keep threatening you.", "HARASSMENT"),
      Fixture("Harassment", "I will stalk you and dox your address.", "HARASSMENT"),
      Fixture("Phishing", "Urgent: your login is suspended, click here and send your password.", "PHISHING_CREDENTIAL_THEFT"),
      Fixture("Phishing", "Action required: confirm your bank verification code immediately.", "PHISHING_CREDENTIAL_THEFT"),
    ).let { seed -> List(6) { seed }.flatten() }
    val started = System.nanoTime()
    val predictions = fixtures.map { CommunicationRiskDetector.classify(it.title, it.body)?.category }
    val elapsedNanos = System.nanoTime() - started
    val categories = listOf("SELF_HARM", "SEXUAL_CONTENT", "SEXUAL_SOLICITATION", "GROOMING", "HARASSMENT", "PHISHING_CREDENTIAL_THEFT")
    categories.forEach { category ->
      val truePositives = fixtures.indices.count { fixtures[it].expected == category && predictions[it] == category }
      val falsePositives = fixtures.indices.count { fixtures[it].expected != category && predictions[it] == category }
      val falseNegatives = fixtures.indices.count { fixtures[it].expected == category && predictions[it] != category }
      val precision = truePositives.toDouble() / (truePositives + falsePositives)
      val recall = truePositives.toDouble() / (truePositives + falseNegatives)
      println("COMMUNICATION_RULES_CATEGORY category=$category precision=$precision recall=$recall")
      check(precision >= 0.8)
      check(recall >= 0.8)
    }
    println("COMMUNICATION_RULES_MEASUREMENT fixtures=${fixtures.size} runtimeNanos=$elapsedNanos batteryMeasurement=UNAVAILABLE")
    check(elapsedNanos > 0)
  }
}
