package expo.modules.guardianprotection.content

import java.time.Instant
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.assertThrows
import org.junit.Test

class ContentRiskContractsTest {
  @Test
  fun `verdict retains signal provenance without raw content`() {
    val verdict = ContentRiskVerdict(
      signalSource = SignalSource.ACCESSIBILITY_TEXT,
      category = ContentRiskCategory.SELF_HARM_SUICIDE,
      severity = ContentRiskSeverity.HIGH,
      confidence = 0.91,
      reasonCodes = setOf("SELF_HARM_DIRECT"),
      classifierVersion = "rules-v1",
      capabilityLevel = ContentCapabilityLevel.BEST_EFFORT,
      action = ContentAction.BLOCK_AND_REQUEST,
    )
    assertEquals(SignalSource.ACCESSIBILITY_TEXT, verdict.signalSource)
  }

  @Test
  fun `defaults are age adaptive while legacy policy falls back safely`() {
    assertEquals(ContentRiskSeverity.MEDIUM, ContentRiskPolicy.blockThreshold("YOUNG_CHILD", null))
    assertEquals(ContentRiskSeverity.MEDIUM, ContentRiskPolicy.blockThreshold("PRETEEN", null))
    assertEquals(ContentRiskSeverity.HIGH, ContentRiskPolicy.blockThreshold("TEEN", null))
    assertEquals(ContentRiskSeverity.CRITICAL, ContentRiskPolicy.blockThreshold("OLDER_TEEN", null))
    assertEquals(ContentRiskSeverity.HIGH, ContentRiskPolicy.blockThreshold("TEEN", "HIGH"))
    assertEquals(
      ContentRiskSeverity.MEDIUM,
      ContentRiskPolicy.parseSignedThreshold("PRETEEN", null),
    )
    assertEquals(
      ContentRiskSeverity.CRITICAL,
      ContentRiskPolicy.parseSignedThreshold(
        "OLDER_TEEN",
        mapOf("content_block_threshold" to "CRITICAL"),
      ),
    )
    assertThrows(IllegalArgumentException::class.java) {
      ContentRiskPolicy.parseSignedThreshold("TEEN", mapOf("content_block_threshold" to "INVALID"))
    }
  }

  @Test
  fun `content approval matches only the exact device app and keyed fingerprint before expiry`() {
    val now = Instant.parse("2026-08-16T12:00:00Z")
    val approval = ContentApproval(
      deviceId = "device-a",
      appRef = "com.example.video",
      fingerprint = "a".repeat(64),
      expiresAt = Instant.parse("2026-08-16T12:15:00Z"),
    )
    assertTrue(ContentReviewApprovalMatcher.matches(listOf(approval), "device-a", "com.example.video", "a".repeat(64), now))
    assertFalse(ContentReviewApprovalMatcher.matches(listOf(approval), "device-b", "com.example.video", "a".repeat(64), now))
    assertFalse(ContentReviewApprovalMatcher.matches(listOf(approval), "device-a", "com.example.other", "a".repeat(64), now))
    assertFalse(ContentReviewApprovalMatcher.matches(listOf(approval), "device-a", "com.example.video", "b".repeat(64), now))
    assertFalse(ContentReviewApprovalMatcher.matches(listOf(approval), "device-a", "com.example.video", "a".repeat(64), Instant.parse("2026-08-16T12:15:00Z")))
  }

  @Test
  fun `minimized review evidence rejects raw identifiers malformed fingerprints and invalid public refs`() {
    ContentReviewEvidence(
      appRef = "com.example.video",
      fingerprint = "a".repeat(64),
      category = ContentRiskCategory.SELF_HARM_SUICIDE,
      severity = ContentRiskSeverity.HIGH,
      confidence = 0.91,
      reasonCode = "SELF_HARM_DIRECT+SELF_HARM_INTENT",
      publicContentProvider = "YOUTUBE",
      publicContentId = "dQw4w9WgXcQ",
    )
    assertThrows(IllegalArgumentException::class.java) {
      ContentReviewEvidence(
        appRef = "com.example video",
        fingerprint = "A".repeat(64),
        category = ContentRiskCategory.SELF_HARM_SUICIDE,
        severity = ContentRiskSeverity.HIGH,
        confidence = 0.91,
        reasonCode = "raw text is prohibited",
      )
    }
  }
}
