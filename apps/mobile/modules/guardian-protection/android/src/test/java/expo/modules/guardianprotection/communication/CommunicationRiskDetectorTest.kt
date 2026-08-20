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
  fun `runtime is app agnostic and throttles duplicate notifications`() {
    val emitted = mutableListOf<String>()
    CommunicationSafetyRuntime.setEnabled(true)
    CommunicationSafetyRuntime.setListener { _, packageName -> emitted.add(packageName) }
    CommunicationSafetyRuntime.processNotification(
      "com.future.messenger",
      "Urgent",
      "Your login is suspended, click here and send your password",
      "msg",
      "chat",
      1_000L,
    )
    CommunicationSafetyRuntime.processNotification(
      "com.future.messenger",
      "Urgent",
      "Your login is suspended, click here and send your password",
      "msg",
      "chat",
      2_000L,
    )
    CommunicationSafetyRuntime.processNotification(
      "com.future.messenger",
      "Urgent",
      "Your login is suspended, click here and send your password",
      "msg",
      "chat",
      3_000L,
    )
    assertEquals(listOf("com.future.messenger"), emitted)
    CommunicationSafetyRuntime.setListener(null)
    CommunicationSafetyRuntime.setEnabled(false)
  }

  @Test
  fun `labelled fixture reports per category precision recall runtime and battery limitation`() {
    data class Fixture(
      val id: String,
      val title: String,
      val body: String,
      val expected: String?,
      val adversarial: Boolean = false,
    )

    fun fixture(
      id: String,
      category: String,
      body: String,
      adversarial: Boolean = false,
    ) = Fixture(id, category.replace('_', ' '), body, category, adversarial)

    val negatives = listOf(
      Fixture("negative-001", "Homework", "The homework problem asks about suicide rates in history.", null),
      Fixture("negative-002", "News", "News headline: new safety rules announced today.", null),
      Fixture("negative-003", "Lyrics", "The song says 'kill myself' in the chorus.", null),
      Fixture("negative-004", "Medical", "The doctor discussed self-harm warning signs.", null),
      Fixture("negative-005", "One word", "nudes", null),
      Fixture("negative-006", "Dinner", "Send me the recipe photo.", null),
      Fixture("negative-007", "Class", "We should meet in the library tomorrow.", null),
      Fixture("negative-008", "Sports", "The team captain will threaten the record.", null),
      Fixture("negative-009", "Bank lesson", "Our homework covers password security.", null),
      Fixture("negative-010", "Book report", "The novel describes a character planning suicide.", null),
      Fixture("negative-011", "Health class", "We learned how to recognize self-harm warning signs.", null),
      Fixture("negative-012", "Theater", "The script says, 'I will hurt you,' in act two.", null),
      Fixture("negative-013", "Photography", "Please share the picture from our family picnic.", null),
      Fixture("negative-014", "Cooking", "Can you send me the photo of your recipe?", null),
      Fixture("negative-015", "Art class", "The teacher asked us to draw an explicit color contrast.", null),
      Fixture("negative-016", "Science", "The article explains sexual reproduction in plants.", null),
      Fixture("negative-017", "News report", "The paper reported a sexual assault case yesterday.", null),
      Fixture("negative-018", "Age question", "How old is the historic bridge?", null),
      Fixture("negative-019", "Meeting", "Let's meet alone in the library to study.", null),
      Fixture("negative-020", "Privacy lesson", "Our class discussed why passwords must stay secret.", null),
      Fixture("negative-021", "Password manager", "Your password manager can autofill the login.", null),
      Fixture("negative-022", "Bank notice", "The bank's security notice explains verification codes.", null),
      Fixture("negative-023", "Sports threat", "The storm threatens to cancel the game.", null),
      Fixture("negative-024", "Address book", "I will send your address to the delivery driver.", null),
      Fixture("negative-025", "Calendar", "The event is scheduled for tonight at eight.", null),
      Fixture("negative-026", "Travel", "Please confirm your hotel booking at the front desk.", null),
      Fixture("negative-027", "Recipe group", "Show me that picture of the finished cake.", null),
      Fixture("negative-028", "Museum", "The museum exhibit includes explicit historical material.", null),
      Fixture("negative-029", "Medical form", "Please confirm your medical verification code with reception.", null),
      Fixture("negative-030", "School account", "Action required: update your school profile by Friday.", null),
      Fixture("negative-031", "Choir", "The lyrics mention being unable to go on.", null),
      Fixture("negative-032", "Book club", "The author wrote about meeting someone alone.", null),
      Fixture("negative-033", "Parent", "Don't tell anyone about the birthday surprise.", null),
      Fixture("negative-034", "Weather", "The forecast says the storm will hurt the crops.", null),
      Fixture("negative-035", "Debate", "The speaker threatened to change the policy.", null),
      Fixture("negative-036", "Community", "The group will report suspicious login messages.", null),
      Fixture("negative-037", "School photo", "Could you forward the class picture to me?", null),
      Fixture("negative-038", "Astronomy", "The satellite will pass overhead tonight.", null),
      Fixture("negative-039", "History", "The lesson covers how young soldiers met in wartime.", null),
      Fixture("negative-040", "Security", "Never send me your password or one-time code.", null),
      Fixture("negative-041", "Support", "Your account is safe; no action is required.", null),
      Fixture("negative-042", "Recipe", "Share the intimate details of your new recipe.", null),
      Fixture("negative-043", "Poetry", "The poem says there is no reason to live.", null),
      Fixture("negative-044", "Journalism", "The headline quotes a threat made during court.", null),
      Fixture("negative-045", "Medical news", "News: doctors study sexual assault recovery.", null),
      Fixture("negative-046", "Meeting invite", "Please keep this calendar invite between us.", null),
      Fixture("negative-047", "Password class", "The teacher said to verify now before the quiz.", null),
      Fixture("negative-048", "Travel photo", "Send a picture of the passport cover, not its number.", null),
      Fixture("negative-049", "Game", "The game character says kill you when defeated.", null),
      Fixture("negative-050", "School safety", "The counselor explained what grooming means.", null),
      Fixture("negative-051", "Drama", "The actor will stalk the suspect in the next scene.", null),
      Fixture("negative-052", "News alert", "Urgent news: the website asks readers to verify facts.", null),
      Fixture("negative-053", "Study group", "Can you show me your notes privately after class?", null),
      Fixture("negative-054", "Family", "Meet me alone so we can wrap your present.", null),
      Fixture("negative-055", "Health", "I don't want to go on with this workout plan.", null),
      Fixture("negative-056", "Work", "The login page says action required for all employees.", null),
      Fixture("negative-057", "Gardening", "The plants need explicit labels for each seed tray.", null),
      Fixture("negative-058", "Photo backup", "Your private picture is backed up securely.", null),
      Fixture("negative-059", "Sports", "The coach said you will regret skipping practice.", null),
      Fixture("negative-060", "Library", "Please don't tell anyone which book I borrowed.", null),
    )
    val positives = listOf(
      fixture("self-harm-001", "SELF_HARM", "I am going to kill myself tonight."),
      fixture("self-harm-002", "SELF_HARM", "I plan to end my life and there is no reason to live."),
      fixture("self-harm-003", "SELF_HARM", "I want to self-harm and I can't go on anymore."),
      fixture("self-harm-004", "SELF_HARM", "Tonight I am going to kill myself; I have a plan."),
      fixture("self-harm-005", "SELF_HARM", "I want to end my life and I am going to do it."),
      fixture("self-harm-006", "SELF_HARM", "I can't go on, I want to hurt myself tonight."),
      fixture("self-harm-007", "SELF_HARM", "My plan is to kill myself because I have no reason to live."),
      fixture("self-harm-008", "SELF_HARM", "I am going to self-harm tonight; I can't go on."),
      fixture("self-harm-009", "SELF_HARM", "I don't want to be here anymore.", true),
      fixture("self-harm-010", "SELF_HARM", "There is no way out and I am done with life.", true),
      fixture("sexual-content-001", "SEXUAL_CONTENT", "Please send explicit photos and nudes."),
      fixture("sexual-content-002", "SEXUAL_CONTENT", "This contains explicit sexual assault material."),
      fixture("sexual-content-003", "SEXUAL_CONTENT", "The explicit porn content was sent in the chat."),
      fixture("sexual-content-004", "SEXUAL_CONTENT", "That sexual assault image is explicit and disturbing."),
      fixture("sexual-content-005", "SEXUAL_CONTENT", "The message contains porn material and explicit content."),
      fixture("sexual-content-006", "SEXUAL_CONTENT", "Explicit sexual abuse material was shared here."),
      fixture("sexual-content-007", "SEXUAL_CONTENT", "This is sexual content, not a normal photo."),
      fixture("sexual-content-008", "SEXUAL_CONTENT", "The explicit image depicts sexual assault."),
      fixture("sexual-content-009", "SEXUAL_CONTENT", "That clip was inappropriate and too much.", true),
      fixture("sexual-content-010", "SEXUAL_CONTENT", "Look at this private thing I found.", true),
      fixture("sexual-solicitation-001", "SEXUAL_SOLICITATION", "Share a nude picture with me."),
      fixture("sexual-solicitation-002", "SEXUAL_SOLICITATION", "Please share an intimate picture."),
      fixture("sexual-solicitation-003", "SEXUAL_SOLICITATION", "Send me a private sexual photo."),
      fixture("sexual-solicitation-004", "SEXUAL_SOLICITATION", "Show me your nude picture privately."),
      fixture("sexual-solicitation-005", "SEXUAL_SOLICITATION", "Trade an explicit photo with me."),
      fixture("sexual-solicitation-006", "SEXUAL_SOLICITATION", "Forward that intimate picture to me."),
      fixture("sexual-solicitation-007", "SEXUAL_SOLICITATION", "Can you send a sexual pic now?"),
      fixture("sexual-solicitation-008", "SEXUAL_SOLICITATION", "Please show me the nude photo."),
      fixture("sexual-solicitation-009", "SEXUAL_SOLICITATION", "Send me that private thing.", true),
      fixture("sexual-solicitation-010", "SEXUAL_SOLICITATION", "Can you share what you are wearing?", true),
      fixture("grooming-001", "GROOMING", "Keep this secret, how old are you?"),
      fixture("grooming-002", "GROOMING", "Don't tell anyone; meet me alone, are you underage?"),
      fixture("grooming-003", "GROOMING", "Just between us, how old are you?"),
      fixture("grooming-004", "GROOMING", "Hide this from your parents and meet me alone."),
      fixture("grooming-005", "GROOMING", "Keep this secret; are you underage?"),
      fixture("grooming-006", "GROOMING", "Don't tell anyone, how old are you really?"),
      fixture("grooming-007", "GROOMING", "Meet me alone; keep this between us."),
      fixture("grooming-008", "GROOMING", "Hide this and tell me your age."),
      fixture("grooming-009", "GROOMING", "Don't tell anyone I am older than I look.", true),
      fixture("grooming-010", "GROOMING", "You can trust me; our secret is safe.", true),
      fixture("harassment-001", "HARASSMENT", "I will hurt you and keep threatening you."),
      fixture("harassment-002", "HARASSMENT", "I will stalk you and dox your address."),
      fixture("harassment-003", "HARASSMENT", "Stop hiding; I will hurt you tonight."),
      fixture("harassment-004", "HARASSMENT", "I will threaten you again if you tell anyone."),
      fixture("harassment-005", "HARASSMENT", "I will stalk you and threaten your family."),
      fixture("harassment-006", "HARASSMENT", "You will get hurt; I keep threatening you."),
      fixture("harassment-007", "HARASSMENT", "I will doxx you and hurt you."),
      fixture("harassment-008", "HARASSMENT", "They keep stalking you and threatening you."),
      fixture("harassment-009", "HARASSMENT", "You'll regret crossing me.", true),
      fixture("harassment-010", "HARASSMENT", "I know where you live.", true),
      fixture("phishing-001", "PHISHING_CREDENTIAL_THEFT", "Urgent: your login is suspended, click here and send me your password."),
      fixture("phishing-002", "PHISHING_CREDENTIAL_THEFT", "Action required: confirm your bank verification code immediately."),
      fixture("phishing-003", "PHISHING_CREDENTIAL_THEFT", "Your password expires now; click to verify your login."),
      fixture("phishing-004", "PHISHING_CREDENTIAL_THEFT", "Urgent bank alert: send the one-time code immediately."),
      fixture("phishing-005", "PHISHING_CREDENTIAL_THEFT", "Your account is suspended; tap here and confirm your passcode."),
      fixture("phishing-006", "PHISHING_CREDENTIAL_THEFT", "Verify now: your login requires the password and code."),
      fixture("phishing-007", "PHISHING_CREDENTIAL_THEFT", "Action required to unlock your bank account; click here."),
      fixture("phishing-008", "PHISHING_CREDENTIAL_THEFT", "Immediately confirm your verification code at the link."),
      fixture("phishing-009", "PHISHING_CREDENTIAL_THEFT", "Your access needs attention; follow the instructions.", true),
      fixture("phishing-010", "PHISHING_CREDENTIAL_THEFT", "Please review the account message when you can.", true),
    )
    val fixtures = negatives + positives
    check(fixtures.size >= 100)
    check(fixtures.map { it.id }.toSet().size == fixtures.size)
    check(fixtures.map { "${it.title}\u0000${it.body}" }.toSet().size == fixtures.size)
    val started = System.nanoTime()
    val predictions = fixtures.map { CommunicationRiskDetector.classify(it.title, it.body)?.category }
    val elapsedNanos = System.nanoTime() - started
    val categories = listOf("SELF_HARM", "SEXUAL_CONTENT", "SEXUAL_SOLICITATION", "GROOMING", "HARASSMENT", "PHISHING_CREDENTIAL_THEFT")
    categories.forEach { category ->
      val truePositives = fixtures.indices.count { fixtures[it].expected == category && predictions[it] == category }
      val falsePositives = fixtures.indices.count { fixtures[it].expected != category && predictions[it] == category }
      val falseNegatives = fixtures.indices.count { fixtures[it].expected == category && predictions[it] != category }
      val falsePositiveIds = fixtures.indices
        .filter { fixtures[it].expected != category && predictions[it] == category }
        .map { fixtures[it].id }
      val falseNegativeIds = fixtures.indices
        .filter { fixtures[it].expected == category && predictions[it] != category }
        .map { fixtures[it].id }
      val precision = truePositives.toDouble() / (truePositives + falsePositives)
      val recall = truePositives.toDouble() / (truePositives + falseNegatives)
      val adversarialMisses = fixtures.indices
        .filter { fixtures[it].expected == category && fixtures[it].adversarial && predictions[it] != category }
        .map { fixtures[it].id }
      println(
        "COMMUNICATION_RULES_CATEGORY category=$category precision=$precision " +
          "recall=$recall falsePositives=$falsePositives falseNegatives=$falseNegatives " +
          "falsePositiveIds=${falsePositiveIds.joinToString(",").ifEmpty { "none" }} " +
          "falseNegativeIds=${falseNegativeIds.joinToString(",").ifEmpty { "none" }} " +
          "adversarialMisses=${adversarialMisses.joinToString(",").ifEmpty { "none" }}",
      )
    }
    println(
      "COMMUNICATION_RULES_MEASUREMENT uniqueFixtures=${fixtures.size} " +
        "runtimeNanos=$elapsedNanos batteryMeasurement=UNAVAILABLE",
    )
    check(elapsedNanos > 0)
  }
}
