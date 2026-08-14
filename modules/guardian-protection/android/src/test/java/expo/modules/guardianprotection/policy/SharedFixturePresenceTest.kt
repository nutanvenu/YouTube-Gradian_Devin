package expo.modules.guardianprotection.policy

import java.io.File
import java.time.Instant
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertTrue
import org.junit.Test

class SharedFixturePresenceTest {
  @Test
  fun sharedDecisionFixtureIsParsedByTheNativeTestSource() {
    val fixture = File(projectRoot(), "packages/test-fixtures/policy-decision-cases.json")
    assertTrue("shared policy fixture is missing: ${fixture.absolutePath}", fixture.isFile)
    val root = JSONObject(fixture.readText())
    assertTrue(root.has("bundles"))
    assertTrue(root.has("cases"))
    assertTrue(root.has("rejected_bundles"))
    assertTrue(root.getJSONArray("cases").length() >= 36)
  }

  @Test
  fun everySharedDecisionCaseMatchesTheNativeEvaluator() {
    val root = JSONObject(File(projectRoot(), "packages/test-fixtures/policy-decision-cases.json").readText())
    val bundles = root.getJSONObject("bundles")
    val evaluator = PolicyEvaluator()
    for (index in 0 until root.getJSONArray("cases").length()) {
      val case = root.getJSONArray("cases").getJSONObject(index)
      val bundle = jsonMap(bundles.getJSONObject(case.getString("bundle_ref")))
      val base = jsonMap(case.getJSONObject("context"))
      val target = case.getJSONObject("context").getJSONObject("target")
      val usage = case.getJSONObject("context").getJSONObject("usage")
      val targetKind = target.getString("kind")
      val targetRef = target.getString("ref")
      val decision = evaluator.evaluate(
        snapshot(bundle),
        PolicyContext(
          now = Instant.parse(case.getJSONObject("context").getString("timestamp")),
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
          currentManualRoutineId = case.getJSONObject("context").optString("current_manual_routine_id").takeIf { it.isNotEmpty() },
          timezone = case.getJSONObject("context").optString("timezone").takeIf { it.isNotEmpty() },
        ),
      )
      val expected = case.getJSONObject("expected")
      if (expected.getString("reason_code") == "TAMPERED_SIGNATURE") {
        assertTrue("${case.getString("id")} is a rejected signature case", case.getString("id") == "tampered-signature")
        continue
      }
      assertTrue("${case.getString("id")} action", expected.getString("action") == decision.action)
      assertTrue("${case.getString("id")} reason", expected.getString("reason_code") == decision.reasonCode)
      assertTrue("${case.getString("id")} rule", expected.optString("policy_rule_id").ifEmpty { null } == decision.policyRuleId)
      assertTrue("${case.getString("id")} stale", expected.getBoolean("bundle_stale") == decision.bundleStale)
    }
  }

  private fun projectRoot(): File {
    var current = File(requireNotNull(System.getProperty("user.dir")))
    while (!File(current, "packages/test-fixtures/policy-decision-cases.json").isFile) {
      val parent = current.parentFile ?: break
      current = parent
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
