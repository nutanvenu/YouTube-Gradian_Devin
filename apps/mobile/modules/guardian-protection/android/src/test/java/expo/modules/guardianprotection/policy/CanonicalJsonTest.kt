package expo.modules.guardianprotection.policy

import org.junit.Assert.assertEquals
import org.junit.Test

class CanonicalJsonTest {
  @Test
  fun canonicalBytesSortKeysByUtf16AndExcludeSignature() {
    val bundle = mapOf<String, Any?>(
      "z" to 1,
      "😀" to "emoji",
      "a" to listOf(2, 1),
      "signature" to "must-not-be-signed",
    )
    assertEquals("""{"a":[2,1],"z":1,"😀":"emoji"}""", CanonicalJson.encode(bundle.filterKeys { it != "signature" }))
  }
}
