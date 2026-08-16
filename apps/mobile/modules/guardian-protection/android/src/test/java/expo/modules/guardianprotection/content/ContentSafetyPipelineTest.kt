package expo.modules.guardianprotection.content

import android.view.accessibility.AccessibilityEvent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ContentSafetyPipelineTest {
  private val fingerprintKey = ByteArray(32) { (it + 1).toByte() }

  @Test
  fun `normalizes Unicode then emits only a minimized thresholded event`() {
    val rawCanary = "Ｓｅｌｆ\u200b-harm plan tonight RAW-CANARY-DO-NOT-PERSIST"
    val event = ContentSafetyPipeline(DeterministicContentRiskClassifier()).inspect(
      ContentObservation(
        source = SignalSource.NOTIFICATION,
        appRef = "com.future.chat",
        title = "Message",
        text = rawCanary,
        capabilityLevel = ContentCapabilityLevel.BEST_EFFORT,
      ),
      blockThreshold = ContentRiskSeverity.MEDIUM,
      fingerprintKey = fingerprintKey,
    )

    requireNotNull(event)
    assertEquals(ContentRiskCategory.SELF_HARM_SUICIDE, event.category)
    assertEquals(ContentAction.BLOCK_AND_REQUEST, event.action)
    assertEquals(64, event.fingerprint.length)
    assertFalse(event.toString().contains("RAW-CANARY"))
    assertFalse(event.toPersistedMap().values.any { it.toString().contains("RAW-CANARY") })
  }

  @Test
  fun `educational news and negated contexts do not create a content-risk event`() {
    val pipeline = ContentSafetyPipeline(DeterministicContentRiskClassifier())
    val benign = listOf(
      "News lesson: suicide prevention resources help students stay safe.",
      "Do not hurt yourself; call a trusted adult for help.",
      "A history documentary discusses violence in a museum exhibit.",
    )
    benign.forEach { text ->
      assertNull(
        pipeline.inspect(
          ContentObservation(
            source = SignalSource.MEDIA_METADATA,
            appRef = "com.future.video",
            title = text,
            text = null,
            capabilityLevel = ContentCapabilityLevel.BEST_EFFORT,
          ),
          ContentRiskSeverity.MEDIUM,
          fingerprintKey,
        ),
      )
    }
  }

  @Test
  fun `notification filter accepts future user apps but excludes system OTP financial and media controls`() {
    assertTrue(NotificationContentFilter.shouldInspect("com.future.messenger", false, null, null, "Watch this", null))
    assertFalse(NotificationContentFilter.shouldInspect("com.android.systemui", true, "msg", null, "Watch this", null))
    assertFalse(NotificationContentFilter.shouldInspect("com.future.messenger", false, "msg", "chat", "Your verification code", "123456"))
    assertFalse(NotificationContentFilter.shouldInspect("com.future.messenger", false, "msg", "bank", "Bank alert", "Balance \$50"))
    assertFalse(NotificationContentFilter.shouldInspect("com.future.music", false, "transport", "media", "Song title", "Artist"))
  }

  @Test
  fun `runtime can use persisted policy without a JavaScript listener`() {
    val emitted = mutableListOf<MinimizedContentRiskEvent>()
    val runtime = ContentSafetyRuntime(
      policy = {
        ContentSafetyPolicy(
          notificationEnabled = true,
          accessibilitySignalsEnabled = true,
          blockThreshold = ContentRiskSeverity.MEDIUM,
        )
      },
      fingerprintKey = fingerprintKey,
      eventSink = emitted::add,
      classifier = DeterministicContentRiskClassifier(),
    )

    val event = runtime.processNotification(
      packageName = "com.future.social",
      isSystemApp = false,
      notificationCategory = "msg",
      channelId = "direct",
      title = "Urgent",
      text = "I am going to kill myself tonight",
    )

    assertNotNull(event)
    assertEquals(1, emitted.size)
    assertEquals(ContentAction.BLOCK_AND_REQUEST, emitted.single().action)
  }

  @Test
  fun `accessibility inspection is consent and event gated before text is read`() {
    assertFalse(AccessibilityContentGate.shouldInspect(false, true, AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED))
    assertFalse(AccessibilityContentGate.shouldInspect(true, false, AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED))
    assertFalse(AccessibilityContentGate.shouldInspect(true, true, AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED))
    assertTrue(AccessibilityContentGate.shouldInspect(true, true, AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED))
    assertTrue(AccessibilityContentGate.shouldInspect(true, true, AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED))
  }

  @Test
  fun `normalization is bounded and removes invisible Unicode controls`() {
    val normalized = ContentTextNormalizer.normalize("A\u200b" + "x".repeat(2_000))
    assertFalse(normalized.contains('\u200b'))
    assertTrue(normalized.length <= ContentTextNormalizer.MAX_NORMALIZED_CHARS)
  }
}
