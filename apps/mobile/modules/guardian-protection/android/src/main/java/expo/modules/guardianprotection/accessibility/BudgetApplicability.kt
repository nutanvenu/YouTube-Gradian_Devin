package expo.modules.guardianprotection.accessibility

import expo.modules.guardianprotection.policy.CompiledPolicySnapshot
import java.time.Instant

object BudgetApplicability {
  fun hasApplicableAppBudget(
    snapshot: CompiledPolicySnapshot,
    packageName: String,
    category: String?,
    now: Instant = Instant.now(),
  ): Boolean {
    val appRule = snapshot.appRules[packageName]
    val categoryRule = category?.let { snapshot.categoryRules[it] }
    val explicitRule = appRule ?: categoryRule
    if (isLimit(explicitRule)) return true

    val activeOverride = snapshot.temporaryOverrides.firstOrNull { rule ->
      appliesTo(rule, packageName, category) && isActive(rule, now)
    }
    if (activeOverride != null) return isLimit(activeOverride)

    val deviceBudget = snapshot.basePolicy["daily_device_budget_minutes"] as? Number
    val deviceBudgetApplies = explicitRule == null ||
      (explicitRule["action"] != "BLOCK" &&
        explicitRule["action"] != "UNLIMITED" &&
        explicitRule["exclude_from_budget"] != true)
    return deviceBudget != null && deviceBudgetApplies
  }

  private fun isLimit(rule: Map<String, Any?>?): Boolean =
    rule?.get("action") == "LIMIT" && rule["daily_minutes"] is Number

  private fun appliesTo(rule: Map<String, Any?>, packageName: String, category: String?): Boolean =
    when (rule["target_kind"]) {
      "APP" -> rule["target_ref"] == packageName
      "CATEGORY" -> rule["target_ref"] == category
      "DEVICE" -> true
      else -> false
    }

  private fun isActive(rule: Map<String, Any?>, now: Instant): Boolean {
    val startsAt = instant(rule["starts_at"]) ?: return false
    val expiresAt = instant(rule["expires_at"]) ?: return false
    return !now.isBefore(startsAt) && now.isBefore(expiresAt)
  }

  private fun instant(value: Any?): Instant? =
    (value as? String)?.let { runCatching { Instant.parse(it) }.getOrNull() }
}
