import Foundation

public struct PolicyDecision: Equatable, Sendable, Codable {
  public let action: String
  public let reasonCode: String
  public let policyRuleID: String?
  public let bundleStale: Bool

  public init(action: String, reasonCode: String, policyRuleID: String?, bundleStale: Bool) {
    self.action = action
    self.reasonCode = reasonCode
    self.policyRuleID = policyRuleID
    self.bundleStale = bundleStale
  }
}

public enum GuardianPolicyEvaluator {
  public static func evaluate(bundle: JSONValue, context: JSONValue) -> PolicyDecision {
    guard let bundleObject = bundle.objectValue, let contextObject = context.objectValue else {
      return blocked("INVALID_POLICY", nil)
    }
    let stale = isSoftExpired(bundleObject, timestamp: contextObject["timestamp"]?.stringValue)
    let base = bundleObject["base_policy"]?.objectValue ?? [:]
    let target = contextObject["target"]?.objectValue ?? [:]
    let kind = target["kind"]?.stringValue ?? ""
    let ref = target["ref"]?.stringValue ?? ""
    let category = target["category"]?.stringValue ?? (kind == "CATEGORY" ? ref : nil)
    let usage = contextObject["usage"]?.objectValue ?? [:]
    let usageSeconds = usageSeconds(usage, kind: kind, ref: ref, category: category)

    if let allow = base["safety_allowlist"]?.arrayValue?.first(where: {
      let value = $0.objectValue
      return value?["target_kind"]?.stringValue == kind && value?["target_ref"]?.stringValue == ref
    }) {
      _ = allow
      return decision("ALLOW", "SAFETY_ALLOWLIST", nil, stale)
    }

    if let override = activeOverride(bundleObject["temporary_overrides"]?.arrayValue, target: target, timestamp: contextObject["timestamp"]?.stringValue) {
      return action(for: override, usageSeconds: usageSeconds, reason: "TEMPORARY_PARENT_OVERRIDE", stale: stale)
    }

    if let routine = activeRoutine(bundleObject["routines"]?.arrayValue, context: contextObject, timestamp: contextObject["timestamp"]?.stringValue, timezone: base["timezone"]?.stringValue ?? "UTC"),
       let action = routineAction(routine, kind: kind, ref: ref, category: category) {
      return decision(action.action, "MANUAL_ROUTINE" == action.reason ? "MANUAL_ROUTINE" : "SCHEDULED_ROUTINE", action.id, stale)
    }

    if let rule = explicitRule(bundleObject["app_rules"]?.arrayValue, target: target, timestamp: contextObject["timestamp"]?.stringValue)
      ?? explicitRule(bundleObject["domain_rules"]?.arrayValue, target: target, timestamp: contextObject["timestamp"]?.stringValue)
      ?? explicitRule(bundleObject["category_rules"]?.arrayValue, target: target, timestamp: contextObject["timestamp"]?.stringValue) {
      return action(for: rule, usageSeconds: usageSeconds, reason: "EXPLICIT_TARGET_RULE", stale: stale)
    }

    if let hard = base["hard_category_rules"]?.arrayValue?.first(where: { $0["category"]?.stringValue == category }) {
      return action(for: hard, usageSeconds: usageSeconds, reason: "AGE_BAND_HARD_CATEGORY", stale: stale)
    }
    if let defaultRule = base["default_category_rules"]?.arrayValue?.first(where: { $0["category"]?.stringValue == category }) {
      return action(for: defaultRule, usageSeconds: usageSeconds, reason: "DEFAULT_CATEGORY_RULE", stale: stale)
    }

    if (base["daily_device_budget_minutes"]?.intValue ?? 0) > 0,
       (usage["device_seconds_today"]?.intValue ?? 0) >= (base["daily_device_budget_minutes"]?.intValue ?? 0) * 60,
       let budgetRule = bundleObject["app_rules"]?.arrayValue?.first(where: { $0["app_ref"]?.stringValue == ref }) {
      let budgetObject = budgetRule.objectValue ?? [:]
      if budgetObject["exclude_from_budget"]?.boolValue != true,
         budgetObject["action"]?.stringValue != "UNLIMITED" {
        return decision("LIMIT_REACHED", "DEVICE_BUDGET_EXHAUSTED", budgetObject["rule_id"]?.stringValue, stale)
      }
    }

    if kind == "APP", let unknown = base["unknown_app_policy"]?.stringValue {
      if unknown == "BLOCK" { return decision("BLOCK", "UNKNOWN_APP_POLICY", nil, stale) }
      if unknown == "LIMIT_AND_NOTIFY" {
        let limit = base["unknown_app_daily_minutes"]?.intValue ?? 0
        return decision(usageSeconds >= limit * 60 ? "LIMIT_REACHED" : "ALLOW_WITH_BUDGET",
                        usageSeconds >= limit * 60 ? "UNKNOWN_APP_BUDGET_EXHAUSTED" : "UNKNOWN_APP_BUDGET_AVAILABLE",
                        nil, stale)
      }
    }
    if kind == "DOMAIN" {
      let policy = base["unknown_domain_policy"]?.stringValue ?? "ALLOW"
      return decision(policy == "BLOCK" || policy == "BLOCK_WHILE_CLASSIFYING" ? "BLOCK" : "ALLOW",
                      "UNKNOWN_DOMAIN_POLICY", nil, stale)
    }
    return decision("ALLOW", "UNKNOWN_APP_POLICY", nil, stale)
  }

  private static func decision(_ action: String, _ reason: String, _ rule: String?, _ stale: Bool) -> PolicyDecision {
    PolicyDecision(action: action, reasonCode: reason, policyRuleID: rule, bundleStale: stale)
  }

  private static func blocked(_ reason: String, _ rule: String?) -> PolicyDecision {
    decision("BLOCK", reason, rule, false)
  }

  private static func isSoftExpired(_ bundle: [String: JSONValue], timestamp: String?) -> Bool {
    guard let expiry = bundle["expires_soft_at"]?.stringValue, let timestamp,
          let expiryDate = ISO8601DateFormatter().date(from: expiry),
          let date = ISO8601DateFormatter().date(from: timestamp) else { return false }
    return date >= expiryDate
  }

  private static func usageSeconds(_ usage: [String: JSONValue], kind: String, ref: String, category: String?) -> Int {
    let key = kind == "APP" ? "app_seconds_today" : "category_seconds_today"
    return usage[key]?.objectValue?[kind == "APP" ? ref : (category ?? ref)]?.intValue
      ?? usage["device_seconds_today"]?.intValue ?? 0
  }

  private static func explicitRule(_ rules: [JSONValue]?, target: [String: JSONValue], timestamp: String?) -> JSONValue? {
    rules?.first(where: { rule in
      let value = rule.objectValue ?? [:]
      let targetKind = target["kind"]?.stringValue
      let targetRef = target["ref"]?.stringValue
      if targetKind == "APP" {
        guard value["app_ref"]?.stringValue == targetRef else { return false }
      }
      if targetKind == "DOMAIN" {
        guard let domain = value["domain"]?.stringValue else { return false }
        guard normalizedDomain(targetRef ?? "") == normalizedDomain(domain) ||
          (value["match"]?.stringValue == "SUBDOMAINS" && normalizedDomain(targetRef ?? "").hasSuffix("." + normalizedDomain(domain)))
        else { return false }
      } else if targetKind == "CATEGORY" {
        guard value["category"]?.stringValue == targetRef else { return false }
      }
      if let schedule = value["schedule"]?.objectValue {
        return isInSchedule(schedule, timestamp: timestamp, timezone: "America/New_York")
      }
      return true
    })
  }

  private static func action(for rule: JSONValue, usageSeconds: Int, reason: String, stale: Bool) -> PolicyDecision {
    let object = rule.objectValue ?? [:]
    let action = object["action"]?.stringValue ?? "BLOCK"
    if action == "ASK_PARENT" { return decision("BLOCK", "REQUIRES_PARENT_APPROVAL", object["rule_id"]?.stringValue, stale) }
    if action == "LIMIT" {
      let exhausted = usageSeconds >= (object["daily_minutes"]?.intValue ?? 0) * 60
      return decision(exhausted ? "LIMIT_REACHED" : "ALLOW_WITH_BUDGET",
                      exhausted ? "BUDGET_EXHAUSTED" : "BUDGET_AVAILABLE",
                      object["rule_id"]?.stringValue, stale)
    }
    return decision(action == "ALLOW" ? "ALLOW" : "BLOCK", reason, object["rule_id"]?.stringValue, stale)
  }

  private static func activeOverride(_ overrides: [JSONValue]?, target: [String: JSONValue], timestamp: String?) -> JSONValue? {
    guard let timestamp, let date = ISO8601DateFormatter().date(from: timestamp) else { return nil }
    return overrides?.first(where: { value in
      let object = value.objectValue ?? [:]
      guard object["target_kind"]?.stringValue == target["kind"]?.stringValue,
            object["target_ref"]?.stringValue == target["ref"]?.stringValue,
            let start = object["starts_at"]?.stringValue.flatMap({ ISO8601DateFormatter().date(from: $0) }),
            let end = object["expires_at"]?.stringValue.flatMap({ ISO8601DateFormatter().date(from: $0) }) else { return false }
      return date >= start && date < end
    })
  }

  private static func activeRoutine(_ routines: [JSONValue]?, context: [String: JSONValue], timestamp: String?, timezone: String) -> (JSONValue, String)? {
    guard let timestamp, let date = ISO8601DateFormatter().date(from: timestamp) else { return nil }
    let manual = context["current_manual_routine_id"]?.stringValue
    if let routine = routines?.first(where: { $0["routine_id"]?.stringValue == manual }) { return (routine, "MANUAL_ROUTINE") }
    for routine in routines ?? [] {
      let object = routine.objectValue ?? [:]
      guard object["kind"]?.stringValue == "SCHEDULED",
            let window = object["window"]?.objectValue,
            let days = window["days"]?.arrayValue?.compactMap(\.intValue),
            let start = window["start"]?.stringValue,
            let end = window["end"]?.stringValue else { continue }
      var calendar = Calendar(identifier: .gregorian)
      calendar.timeZone = TimeZone(identifier: object["timezone"]?.stringValue ?? timezone) ?? .gmt
      let components = calendar.dateComponents([.weekday, .hour, .minute], from: date)
      let isoDay = ((components.weekday ?? 1) + 5) % 7 + 1
      let minute = (components.hour ?? 0) * 60 + (components.minute ?? 0)
      let startMinute = parseMinutes(start)
      let endMinute = parseMinutes(end)
      let active = startMinute < endMinute
        ? days.contains(isoDay) && minute >= startMinute && minute < endMinute
        : (days.contains(isoDay) && minute >= startMinute) || days.contains(isoDay == 1 ? 7 : isoDay - 1) && minute < endMinute
      if active { return (routine, "SCHEDULED_ROUTINE") }
    }
    return nil
  }

  private static func routineAction(_ routine: (JSONValue, String), kind: String, ref: String, category: String?) -> (action: String, reason: String, id: String?)? {
    let object = routine.0.objectValue ?? [:]
    let blockedApps = object["blocked_apps"]?.arrayValue?.compactMap(\.stringValue) ?? []
    let blockedCategories = object["blocked_categories"]?.arrayValue?.compactMap(\.stringValue) ?? []
    if (kind == "APP" && blockedApps.contains(ref)) || (category != nil && blockedCategories.contains(category!)) {
      return ("BLOCK", routine.1, object["routine_id"]?.stringValue)
    }
    return nil
  }

  private static func parseMinutes(_ value: String) -> Int {
    let parts = value.split(separator: ":").compactMap { Int($0) }
    return (parts.first ?? 0) * 60 + (parts.dropFirst().first ?? 0)
  }

  private static func normalizedDomain(_ value: String) -> String {
    let trimmed = value.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "."))
    return trimmed.applyingTransform(.toASCII, reverse: false) ?? trimmed
  }

  private static func isInSchedule(_ schedule: [String: JSONValue], timestamp: String?, timezone: String) -> Bool {
    guard let timestamp, let date = ISO8601DateFormatter().date(from: timestamp),
          let days = schedule["days"]?.arrayValue?.compactMap(\.intValue),
          let start = schedule["start"]?.stringValue,
          let end = schedule["end"]?.stringValue else { return false }
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = TimeZone(identifier: timezone) ?? .gmt
    let components = calendar.dateComponents([.weekday, .hour, .minute], from: date)
    let isoDay = ((components.weekday ?? 1) + 5) % 7 + 1
    let minute = (components.hour ?? 0) * 60 + (components.minute ?? 0)
    let begin = parseMinutes(start)
    let finish = parseMinutes(end)
    return begin < finish
      ? days.contains(isoDay) && minute >= begin && minute < finish
      : (days.contains(isoDay) && minute >= begin) || (days.contains(isoDay == 1 ? 7 : isoDay - 1) && minute < finish)
  }
}
