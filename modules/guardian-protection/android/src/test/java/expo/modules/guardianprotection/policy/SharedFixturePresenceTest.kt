package expo.modules.guardianprotection.policy

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

class SharedFixturePresenceTest {
  @Test
  fun sharedDecisionFixtureIsUsedByTheNativeTestSource() {
    val fixture = File(projectRoot(), "packages/test-fixtures/policy-decision-cases.json")
    assertTrue("shared policy fixture is missing: ${fixture.absolutePath}", fixture.isFile)
    val text = fixture.readText()
    assertTrue(text.contains("\"bundles\""))
    assertTrue(text.contains("\"cases\""))
    assertTrue(text.contains("\"tampered-signature\""))
  }

  private fun projectRoot(): File {
    var current = File(requireNotNull(System.getProperty("user.dir")))
    while (!File(current, "packages/test-fixtures/policy-decision-cases.json").isFile) {
      val parent = current.parentFile ?: break
      current = parent
    }
    return current
  }
}
