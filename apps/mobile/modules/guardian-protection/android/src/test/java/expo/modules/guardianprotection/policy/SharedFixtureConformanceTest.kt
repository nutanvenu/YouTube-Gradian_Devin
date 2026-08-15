package expo.modules.guardianprotection.policy

import java.io.File
import java.time.Instant
import java.util.concurrent.atomic.AtomicInteger
import org.json.JSONArray
import org.json.JSONObject
import org.junit.AfterClass
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.runners.Parameterized

@RunWith(Parameterized::class)
class SharedFixtureConformanceTest(
  private val caseIndex: Int,
  private val caseId: String,
) {
  @Test
  fun evaluatesExpectedDecision() {
    val root = fixtureRoot()
    val fixtureCase = root.getJSONArray("cases").getJSONObject(caseIndex)
    assertEquals(caseId, fixtureCase.getString("id"))
    val bundle = jsonMap(root.getJSONObject("bundles").getJSONObject(fixtureCase.getString("bundle_ref")))
    val context = fixtureCase.getJSONObject("context")
    val target = context.getJSONObject("target")
    val usage = context.getJSONObject("usage")
    val targetKind = target.getString("kind")
    val targetRef = target.getString("ref")
    val decision = PolicyEvaluator().evaluate(
      snapshot(bundle),
      PolicyContext(
        now = Instant.parse(context.getString("timestamp")),
        childId = bundle["child_profile_id"] as String,
        packageName = targetRef.takeIf { targetKind == "APP" },
        domain = targetRef.takeIf { targetKind == "DOMAIN" },
        destinationIp = null,
        usageTodayMs = usageSeconds(usage, targetKind, targetRef) * 1000,
        sessionMs = null,
        activeRoutineIds = emptySet(),
        signal = null,
        category = target.optString("category").takeIf { it.isNotEmpty() }
          ?: targetRef.takeIf { targetKind == "CATEGORY" },
        deviceUsageTodayMs = usage.getLong("device_seconds_today") * 1000,
        currentManualRoutineId = context.optString("current_manual_routine_id").takeIf { it.isNotEmpty() },
        timezone = context.optString("timezone").takeIf { it.isNotEmpty() },
      ),
      signatureValid = caseId != "tampered-signature",
    )
    val expected = fixtureCase.getJSONObject("expected")
    assertEquals("$caseId action", expected.getString("action"), decision.action)
    assertEquals("$caseId reason_code", expected.getString("reason_code"), decision.reasonCode)
    assertEquals(
      "$caseId policy_rule_id",
      expected.optString("policy_rule_id").ifEmpty { null },
      decision.policyRuleId,
    )
    assertEquals("$caseId bundle_stale", expected.getBoolean("bundle_stale"), decision.bundleStale)
    executedCases.incrementAndGet()
  }

  companion object {
    private val executedCases = AtomicInteger()

    @JvmStatic
    @Parameterized.Parameters(name = "{1}")
    fun cases(): List<Array<Any>> {
      val cases = fixtureRoot().getJSONArray("cases")
      return (0 until cases.length()).map { index ->
        arrayOf(index, cases.getJSONObject(index).getString("id"))
      }
    }

    @JvmStatic
    @AfterClass
    fun allCasesExecuted() {
      assertEquals("all shared fixture cases must execute", cases().size, executedCases.get())
    }

    private fun fixtureRoot(): JSONObject {
      val fixture = File(projectRoot(), "packages/test-fixtures/policy-decision-cases.json")
      assertTrue("shared policy fixture is missing: ${fixture.absolutePath}", fixture.isFile)
      return JSONObject(fixture.readText())
    }

    private fun projectRoot(): File {
      var current = File(requireNotNull(System.getProperty("user.dir")))
      while (!File(current, "packages/test-fixtures/policy-decision-cases.json").isFile) {
        current = current.parentFile ?: break
      }
      return current
    }

    private fun snapshot(bundle: Map<String, Any?>): CompiledPolicySnapshot {
      fun records(key: String) = (bundle[key] as List<*>).filterIsInstance<Map<*, *>>().map {
        it.entries.associate { (k, v) -> k as String to v }
      }
      val apps = records("app_rules").mapNotNull { (it["app_ref"] as? String)?.let { ref -> ref to it } }.toMap()
      val categories = records("category_rules").mapNotNull { (it["category"] as? String)?.let { ref -> ref to it } }.toMap()
      return CompiledPolicySnapshot(
        (bundle["policy_version"] as Number).toLong(),
        apps,
        records("domain_rules"),
        categories,
        records("temporary_overrides"),
        records("routines"),
        (bundle["base_policy"] as Map<String, Any?>),
        expiresSoftAt = Instant.parse(bundle["expires_soft_at"] as String),
      )
    }

    private fun usageSeconds(usage: JSONObject, kind: String, ref: String): Long {
      return when (kind) {
        "APP" -> usage.getJSONObject("app_seconds_today").optLong(ref, 0)
        else -> usage.getJSONObject("category_seconds_today").optLong(ref, 0)
      }
    }

    private fun jsonMap(value: JSONObject): Map<String, Any?> =
      value.keys().asSequence().associateWith { key -> jsonValue(value.get(key)) }

    private fun jsonValue(value: Any?): Any? = when (value) {
      JSONObject.NULL -> null
      is JSONObject -> jsonMap(value)
      is JSONArray -> (0 until value.length()).map { jsonValue(value.get(it)) }
      else -> value
    }
  }
}
