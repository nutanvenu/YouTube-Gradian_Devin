package expo.modules.guardianprotection.policy

import java.time.Instant
import java.time.ZoneId

data class PolicyContext(
  val now: Instant,
  val childId: String,
  val packageName: String?,
  val domain: String?,
  val destinationIp: String?,
  val usageTodayMs: Long?,
  val sessionMs: Long?,
  val activeRoutineIds: Set<String>,
  val signal: String?,
  val category: String? = null,
  val deviceUsageTodayMs: Long = 0,
  val currentManualRoutineId: String? = null,
  val timezone: String? = null,
  val reputationVerdict: String? = null,
  val reputationPendingUntil: Instant? = null,
)

data class PolicyDecision(
  val action: String,
  val reasonCode: String,
  val expiresAt: Instant?,
  val policyVersion: Long,
  val policyRuleId: String? = null,
  val bundleStale: Boolean = false,
)

private data class Candidate(
  val action: String,
  val reasonCode: String,
  val ruleId: String?,
  val budgetExempt: Boolean,
  val expiresAt: Instant? = null,
)

class PolicyEvaluator {
  fun evaluate(
    snapshot: CompiledPolicySnapshot,
    context: PolicyContext,
    signatureValid: Boolean = true,
  ): PolicyDecision {
    val base = snapshot.basePolicy
    val targetKind = when {
      context.packageName != null -> "APP"
      context.domain != null -> "DOMAIN"
      else -> "CATEGORY"
    }
    val targetRef = context.packageName ?: context.domain ?: context.category
    val targetCategory = context.category ?: if (targetKind == "CATEGORY") targetRef else null
    val usageSeconds = (context.usageTodayMs ?: 0L) / 1000
    val stale = snapshot.expiresSoftAt?.let { !context.now.isBefore(it) } ?: false
    val deviceExtension = snapshot.temporaryOverrides.firstOrNull { rule ->
      rule["target_kind"] == "DEVICE" &&
        instant(rule["starts_at"])?.let { !context.now.isBefore(it) } == true &&
        instant(rule["expires_at"])?.let { context.now.isBefore(it) } == true
    }?.get("daily_minutes") as? Number

    if (!signatureValid) {
      return PolicyDecision("BLOCK", "TAMPERED_SIGNATURE", null, snapshot.policyVersion, null, stale)
    }

    fun finish(candidate: Candidate): PolicyDecision {
      val deviceBudget = (base["daily_device_budget_minutes"] as? Number)?.toLong()
        ?.plus(deviceExtension?.toLong() ?: 0L)
      if (
        deviceBudget != null &&
        context.deviceUsageTodayMs / 1000 >= deviceBudget * 60 &&
        !candidate.budgetExempt &&
        candidate.action in setOf("ALLOW", "ALLOW_WITH_BUDGET")
      ) {
        return PolicyDecision("LIMIT_REACHED", "DEVICE_BUDGET_EXHAUSTED", candidate.expiresAt, snapshot.policyVersion, candidate.ruleId, stale)
      }
      return PolicyDecision(candidate.action, candidate.reasonCode, candidate.expiresAt, snapshot.policyVersion, candidate.ruleId, stale)
    }

    val safety = (base["safety_allowlist"] as? List<*>).orEmpty().filterIsInstance<Map<*, *>>()
      .firstOrNull { it["target_kind"] == targetKind && it["target_ref"] == targetRef }
    if (safety != null) return finish(Candidate("ALLOW", "SAFETY_ALLOWLIST", null, true))

    val override = snapshot.temporaryOverrides.firstOrNull { rule ->
      val exact = rule["target_kind"] == targetKind && rule["target_ref"] == targetRef
      val categoryMatch = rule["target_kind"] == "CATEGORY" && rule["target_ref"] == targetCategory
      val starts = instant(rule["starts_at"])
      val expires = instant(rule["expires_at"])
      (exact || categoryMatch) && starts != null && expires != null &&
        !context.now.isBefore(starts) && context.now.isBefore(expires)
    }
    if (override != null) return finish(actionFor(override, usageSeconds, "TEMPORARY_PARENT_OVERRIDE", true))

    val manual = context.currentManualRoutineId?.let { id ->
      snapshot.routines.firstOrNull { it["routine_id"] == id && it["kind"] == "MANUAL" }
    }
    manual?.let { routineCandidate(it, targetKind, targetRef, targetCategory, "MANUAL_ROUTINE") }?.let { return finish(it) }

    snapshot.routines.filter { it["kind"] == "SCHEDULED" }.firstNotNullOfOrNull { routine ->
      if (!inWindow(routine["window"] as? Map<*, *>, context.now, context.timezone ?: base["timezone"] as? String ?: "UTC")) {
        null
      } else {
        routineCandidate(routine, targetKind, targetRef, targetCategory, "SCHEDULED_ROUTINE")
      }
    }?.let { return finish(it) }

    val explicit = when (targetKind) {
      "APP" -> snapshot.appRules[targetRef]
      "DOMAIN" -> snapshot.domainTrie.match(targetRef.orEmpty())
      else -> snapshot.categoryRules[targetCategory]
    }
    if (explicit != null) {
      val schedule = explicit["schedule"] as? Map<*, *>
      if (schedule != null && !inWindow(schedule, context.now, context.timezone ?: base["timezone"] as? String ?: "UTC")) {
        return finish(Candidate("BLOCK", "SCHEDULE_OUTSIDE_WINDOW", explicit["rule_id"] as? String, false))
      }
      return finish(actionFor(explicit, usageSeconds, "EXPLICIT_TARGET_RULE", explicit["exclude_from_budget"] == true))
    }

    if (targetCategory != null) {
      val hard = (base["hard_category_rules"] as? List<*>).orEmpty().filterIsInstance<Map<*, *>>()
        .firstOrNull { it["category"] == targetCategory }
      if (hard != null) return finish(actionFor(hard, usageSeconds, "AGE_BAND_HARD_CATEGORY", hard["exclude_from_budget"] == true))
      val defaultRule = (base["default_category_rules"] as? List<*>).orEmpty().filterIsInstance<Map<*, *>>()
        .firstOrNull { it["category"] == targetCategory }
      if (defaultRule != null) return finish(actionFor(defaultRule, usageSeconds, "DEFAULT_CATEGORY_RULE", defaultRule["exclude_from_budget"] == true))
    }

    if (targetKind == "DOMAIN" && context.reputationVerdict in setOf("KNOWN_SAFE", "KNOWN_RISK")) {
      return finish(
        if (context.reputationVerdict == "KNOWN_RISK") {
          Candidate("BLOCK", "REPUTATION_KNOWN_RISK", null, false)
        } else {
          Candidate("ALLOW", "REPUTATION_KNOWN_SAFE", null, false)
        },
      )
    }
    if (targetKind == "DOMAIN" && context.reputationPendingUntil != null) {
      val pending = context.now.isBefore(context.reputationPendingUntil)
      val blockWhileClassifying = base["unknown_domain_policy"] == "BLOCK_WHILE_CLASSIFYING"
      if (pending) {
        return finish(
          Candidate(
            if (blockWhileClassifying) "BLOCK" else "ALLOW",
            if (blockWhileClassifying) "REPUTATION_PENDING" else "REPUTATION_PENDING_NOTIFY",
            null,
            false,
          ),
        )
      }
      return finish(
        Candidate(
          if (blockWhileClassifying) "BLOCK" else "ALLOW",
          if (blockWhileClassifying) "REPUTATION_PENDING_EXPIRED" else "REPUTATION_PENDING_EXPIRED_NOTIFY",
          null,
          false,
        ),
      )
    }

    if (targetKind == "APP" && base["unknown_app_policy"] == "LIMIT_AND_NOTIFY") {
      val limit = (base["unknown_app_daily_minutes"] as? Number)?.toLong() ?: 0
      val exhausted = usageSeconds >= limit * 60
      return finish(Candidate(if (exhausted) "LIMIT_REACHED" else "ALLOW_WITH_BUDGET", if (exhausted) "UNKNOWN_APP_BUDGET_EXHAUSTED" else "UNKNOWN_APP_BUDGET_AVAILABLE", null, false))
    }
    val blocked = if (targetKind == "APP") base["unknown_app_policy"] == "BLOCK"
    else base["unknown_domain_policy"] == "BLOCK" || base["unknown_domain_policy"] == "BLOCK_WHILE_CLASSIFYING"
    return finish(Candidate(if (blocked) "BLOCK" else "ALLOW", if (targetKind == "APP") "UNKNOWN_APP_POLICY" else "UNKNOWN_DOMAIN_POLICY", null, false))
  }

  private fun actionFor(rule: Map<*, *>, usageSeconds: Long, reason: String, budgetExempt: Boolean): Candidate {
    val action = rule["action"] as? String
    val ruleId = rule["rule_id"] as? String
    return when (action) {
      "BLOCK" -> Candidate("BLOCK", reason, ruleId, budgetExempt)
      "ASK_PARENT" -> Candidate("BLOCK", "REQUIRES_PARENT_APPROVAL", ruleId, budgetExempt)
      "LIMIT" -> {
        val limit = (rule["daily_minutes"] as? Number)?.toLong() ?: 0
        val exhausted = usageSeconds >= limit * 60
        Candidate(if (exhausted) "LIMIT_REACHED" else "ALLOW_WITH_BUDGET", if (exhausted) "BUDGET_EXHAUSTED" else "BUDGET_AVAILABLE", ruleId, budgetExempt)
      }
      else -> Candidate("ALLOW", reason, ruleId, budgetExempt || action == "UNLIMITED")
    }
  }

  private fun routineCandidate(routine: Map<*, *>, targetKind: String, targetRef: String?, category: String?, reason: String): Candidate? {
    val ruleId = routine["routine_id"] as? String
    if (targetKind == "APP" && (routine["blocked_apps"] as? List<*>)?.contains(targetRef) == true) return Candidate("BLOCK", reason, ruleId, false)
    if (targetKind == "APP" && (routine["allowed_apps"] as? List<*>)?.contains(targetRef) == true) return Candidate("ALLOW", reason, ruleId, false)
    if (category != null && (routine["blocked_categories"] as? List<*>)?.contains(category) == true) return Candidate("BLOCK", reason, ruleId, false)
    if (category != null && (routine["allowed_categories"] as? List<*>)?.contains(category) == true) return Candidate("ALLOW", reason, ruleId, false)
    if (routine["web_mode"] == "STRICT" && targetKind == "DOMAIN") return Candidate("BLOCK", reason, ruleId, false)
    return null
  }

  private fun inWindow(raw: Map<*, *>?, now: Instant, timezone: String): Boolean {
    if (raw == null) return true
    val local = now.atZone(ZoneId.of(timezone))
    val days = (raw["days"] as? List<*>)?.mapNotNull { (it as? Number)?.toInt() }.orEmpty()
    val start = minutes(raw["start"] as? String ?: return false)
    val end = minutes(raw["end"] as? String ?: return false)
    val current = local.hour * 60 + local.minute
    if (start == end) return days.contains(local.dayOfWeek.value)
    if (start < end) return days.contains(local.dayOfWeek.value) && current >= start && current < end
    val yesterday = if (local.dayOfWeek.value == 1) 7 else local.dayOfWeek.value - 1
    return (days.contains(local.dayOfWeek.value) && current >= start) || (days.contains(yesterday) && current < end)
  }

  private fun minutes(value: String): Int {
    val parts = value.split(":")
    return parts[0].toInt() * 60 + parts[1].toInt()
  }

  private fun instant(value: Any?): Instant? = (value as? String)?.let { runCatching { Instant.parse(it) }.getOrNull() }
}
