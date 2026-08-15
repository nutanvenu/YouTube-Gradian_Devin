package expo.modules.guardianprotection.usage

import org.junit.Assert.assertEquals
import org.junit.Test

class UsageSummaryTest {
  @Test
  fun totalUsesDeviceBucketInsteadOfSummingIndependentNamespaces() {
    assertEquals(
      1_823,
      deviceTotalSeconds(
        mapOf(
          "APP:com.example.chrome" to 1_823,
          "CATEGORY:EDUCATION" to 1_823,
          "DEVICE" to 1_823,
        ),
      ),
    )
  }

  @Test
  fun missingDeviceBucketDoesNotInventACombinedTotal() {
    assertEquals(
      0,
      deviceTotalSeconds(mapOf("APP:com.example.chrome" to 1_823)),
    )
  }
}
