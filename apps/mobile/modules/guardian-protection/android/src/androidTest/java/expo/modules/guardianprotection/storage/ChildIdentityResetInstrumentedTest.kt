package expo.modules.guardianprotection.storage

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import expo.modules.guardianprotection.content.ContentApproval
import expo.modules.guardianprotection.content.ContentBlockReference
import expo.modules.guardianprotection.content.ContentRiskCategory
import expo.modules.guardianprotection.content.ContentRiskSeverity
import java.time.Instant
import java.util.UUID
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ChildIdentityResetInstrumentedTest {
  @Test
  fun clearChildIdentity_removes_usage_and_pending_content_review_for_the_previous_child() {
    val context = ApplicationProvider.getApplicationContext<Context>()
    val preferenceName = "guardian-child-reset-${UUID.randomUUID()}"
    val preferences = context.getSharedPreferences(preferenceName, Context.MODE_PRIVATE)
    try {
      val store = EncryptedPolicyStore(context, preferenceName)
      val now = Instant.now()
      val reference = ContentBlockReference(
        appRef = "com.example.childa",
        fingerprint = "a".repeat(64),
        category = ContentRiskCategory.SELF_HARM_SUICIDE,
        severity = ContentRiskSeverity.CRITICAL,
        confidence = 0.99,
        reasonCode = "TEST_CONTENT_BLOCK",
        occurredAtMillis = now.toEpochMilli(),
      )
      store.swap("{\"child\":\"child-a\"}", 1)
      store.setContentDeviceId("device-a")
      store.addUsage("com.example.childa", 60, 60)
      store.mergeUsageSnapshot("2026-08-21", mapOf("com.example.childa" to 60))
      store.saveActiveContentBlock(reference)
      store.replaceContentApprovals(listOf(ContentApproval("device-a", reference.appRef, reference.fingerprint, now.plusSeconds(60))), now)
      assertTrue(store.enqueueContentReview(reference))

      store.clearChildIdentity()

      assertNull(store.active())
      assertNull(store.contentDeviceId())
      assertNull(store.activeContentBlock())
      assertTrue(store.contentApprovals(now).isEmpty())
      assertTrue(store.pendingContentReviewRequests().isEmpty())
      assertTrue((store.usageSummary(emptyMap())["byTarget"] as Map<*, *>).isEmpty())
      assertTrue(store.usageSnapshots().isEmpty())
      assertFalse(preferences.contains("usage-counters"))
      assertFalse(preferences.contains("usage-snapshots"))
      assertFalse(preferences.contains("content-review-outbox"))
    } finally {
      preferences.edit().clear().commit()
    }
  }
}
