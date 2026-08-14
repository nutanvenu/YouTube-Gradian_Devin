import { Temporal } from "@js-temporal/polyfill";
import { getDomain, getPublicSuffix } from "tldts";
import type {
  PolicyDecision,
  PolicyReasonCode,
  PolicyDecisionAction
} from "@guardian/contracts";
import type {
  AppRule,
  CategoryRule,
  Category,
  DomainRule,
  Routine,
  SignedPolicyBundle,
  TemporaryOverride
} from "./generated.js";

export interface DecisionContext {
  target:
    | { kind: "APP"; ref: string; category?: Category }
    | { kind: "DOMAIN"; ref: string; category?: Category }
    | { kind: "CATEGORY"; ref: string; category?: Category };
  timestamp: string;
  timezone?: string;
  elapsed_usage_seconds?: number;
  reputation_verdict?: "KNOWN_SAFE" | "KNOWN_RISK" | "UNKNOWN";
  current_manual_routine_id?: string;
  signature_valid?: boolean;
}

interface Candidate {
  action: PolicyDecisionAction;
  reason_code: PolicyReasonCode;
  policy_rule_id: string | null;
  daily_minutes?: number;
}

const hardCategories = new Set([
  "ADULT_PORNOGRAPHY",
  "SEXUAL_CONTENT",
  "GAMBLING",
  "DRUGS_CONTROLLED_SUBSTANCES",
  "SELF_HARM_SUICIDE",
  "HATE_EXTREMISM",
  "GRAPHIC_VIOLENCE_GORE",
  "MALWARE",
  "PHISHING_SCAMS"
]);

function localDateTime(timestamp: string, timezone: string): Temporal.ZonedDateTime {
  return Temporal.Instant.from(timestamp).toZonedDateTimeISO(timezone);
}

function minutesSinceMidnight(value: string): number {
  const [hoursText, minutesText] = value.split(":");
  return Number(hoursText) * 60 + Number(minutesText);
}

function isInWindow(window: { days: number[]; start: string; end: string }, dateTime: Temporal.ZonedDateTime): boolean {
  const day = dateTime.dayOfWeek;
  if (!window.days.includes(day)) return false;
  const current = dateTime.hour * 60 + dateTime.minute;
  const start = minutesSinceMidnight(window.start);
  const end = minutesSinceMidnight(window.end);
  if (start === end) return true;
  return start < end ? current >= start && current < end : current >= start || current < end;
}

function normalizedDomain(value: string): string {
  try {
    const withoutScheme = value.includes("://") ? new URL(value).hostname : value;
    const ascii = new URL(`http://${withoutScheme}`).hostname;
    return ascii.toLowerCase().replace(/\.$/, "");
  } catch {
    return "";
  }
}

function domainMatches(rule: DomainRule, target: string): boolean {
  const candidate = normalizedDomain(target);
  const configured = normalizedDomain(rule.domain);
  if (!candidate || !configured) return false;
  if (!getDomain(configured) || !getPublicSuffix(configured) || configured === getPublicSuffix(configured)) {
    return false;
  }
  return rule.match === "EXACT" ? candidate === configured : candidate === configured || candidate.endsWith(`.${configured}`);
}

function actionForRule(
  action: AppRule["action"],
  elapsedSeconds: number,
  dailyMinutes: number | undefined,
  reason: PolicyReasonCode,
  ruleId: string | null
): Candidate {
  if (action === "BLOCK" || action === "ASK_PARENT") {
    return { action: "BLOCK", reason_code: reason, policy_rule_id: ruleId };
  }
  if (action === "LIMIT" && dailyMinutes !== undefined) {
    const exhausted = elapsedSeconds >= dailyMinutes * 60;
    return {
      action: exhausted ? "LIMIT_REACHED" : "ALLOW_WITH_BUDGET",
      reason_code: exhausted ? "BUDGET_EXHAUSTED" : "BUDGET_AVAILABLE",
      policy_rule_id: ruleId,
    };
  }
  if (action === "SCHEDULE") {
    return { action: "ALLOW", reason_code: reason, policy_rule_id: ruleId };
  }
  return { action: "ALLOW", reason_code: reason, policy_rule_id: ruleId };
}

function targetMatchesKind(targetKind: string, target: DecisionContext["target"]): boolean {
  return targetKind === target.kind;
}

function matchesAppRule(rule: AppRule, context: DecisionContext): boolean {
  return context.target.kind === "APP" && rule.app_ref === context.target.ref;
}

function matchesCategoryRule(rule: CategoryRule, context: DecisionContext): boolean {
  return context.target.category !== undefined
    ? rule.category === context.target.category
    : rule.category === context.target.ref;
}

function routineCandidate(
  routine: Routine,
  context: DecisionContext,
  reason: PolicyReasonCode
): Candidate | null {
  if (!isInWindow(routine.window, localDateTime(context.timestamp, context.timezone ?? "UTC"))) {
    return null;
  }
  const target = context.target;
  const category = target.category ?? (target.kind === "CATEGORY" ? target.ref : undefined);
  if (target.kind === "APP" && routine.blocked_apps?.includes(target.ref)) {
    return { action: "BLOCK", reason_code: reason, policy_rule_id: routine.routine_id };
  }
  if (target.kind === "APP" && routine.allowed_apps?.includes(target.ref)) {
    return { action: "ALLOW", reason_code: reason, policy_rule_id: routine.routine_id };
  }
  if (category && routine.blocked_categories?.some((blockedCategory) => blockedCategory === category)) {
    return { action: "BLOCK", reason_code: reason, policy_rule_id: routine.routine_id };
  }
  if (category && routine.allowed_categories?.some((allowedCategory) => allowedCategory === category)) {
    return { action: "ALLOW", reason_code: reason, policy_rule_id: routine.routine_id };
  }
  if (routine.web_mode === "STRICT" && target.kind === "DOMAIN") {
    return { action: "BLOCK", reason_code: reason, policy_rule_id: routine.routine_id };
  }
  return null;
}

function overrideMatches(override: TemporaryOverride, context: DecisionContext): boolean {
  return targetMatchesKind(override.target_kind, context.target) &&
    (override.target_ref === context.target.ref ||
      (context.target.kind === "CATEGORY" && override.target_ref === context.target.category));
}

export function evaluatePolicy(
  bundle: SignedPolicyBundle,
  context: DecisionContext
): PolicyDecision {
  const timezone = context.timezone ?? bundle.base_policy.timezone;
  const elapsedSeconds = Math.max(0, context.elapsed_usage_seconds ?? 0);
  const target = context.target;

  if (context.signature_valid === false) {
    return { action: "BLOCK", reason_code: "TAMPERED_SIGNATURE", policy_rule_id: null };
  }

  const safety = bundle.base_policy.safety_allowlist.find(
    (entry) => targetMatchesKind(entry.target_kind, target) && entry.target_ref === target.ref
  );
  if (safety) return { action: "ALLOW", reason_code: "SAFETY_ALLOWLIST", policy_rule_id: null };

  const activeOverride = bundle.temporary_overrides.find(
    (override) =>
      overrideMatches(override, context) &&
      Temporal.Instant.compare(
        Temporal.Instant.from(context.timestamp),
        Temporal.Instant.from(override.starts_at)
      ) >= 0 &&
      Temporal.Instant.compare(
        Temporal.Instant.from(context.timestamp),
        Temporal.Instant.from(override.expires_at)
      ) < 0
  );
  if (activeOverride) {
    return actionForRule(
      activeOverride.action,
      elapsedSeconds,
      activeOverride.daily_minutes,
      "TEMPORARY_PARENT_OVERRIDE",
      activeOverride.rule_id
    );
  }

  const manual = context.current_manual_routine_id
    ? bundle.routines.find((routine) => routine.routine_id === context.current_manual_routine_id)
    : undefined;
  const manualResult = manual ? routineCandidate(manual, context, "MANUAL_ROUTINE") : null;
  if (manualResult) return manualResult;

  const scheduled = bundle.routines
    .map((routine) => routineCandidate(routine, context, "SCHEDULED_ROUTINE"))
    .find((candidate): candidate is Candidate => candidate !== null);
  if (scheduled) return scheduled;

  const explicit =
    target.kind === "APP"
      ? bundle.app_rules.find((rule) => matchesAppRule(rule, context))
      : target.kind === "DOMAIN"
        ? bundle.domain_rules.find((rule) => domainMatches(rule, target.ref))
        : bundle.category_rules.find((rule) => matchesCategoryRule(rule, context));
  if (explicit) {
    const inSchedule =
      !explicit.schedule ||
      isInWindow(explicit.schedule, localDateTime(context.timestamp, timezone));
    if (explicit.schedule && !inSchedule) {
      return {
        action: "BLOCK",
        reason_code: "SCHEDULE_OUTSIDE_WINDOW",
        policy_rule_id: explicit.rule_id
      };
    }
    return actionForRule(
      explicit.action,
      elapsedSeconds,
      explicit.daily_minutes,
      "EXPLICIT_TARGET_RULE",
      explicit.rule_id
    );
  }

  const category = target.category ?? (target.kind === "CATEGORY" ? target.ref : undefined);
  if (category && hardCategories.has(category)) {
    const hard = bundle.base_policy.hard_category_rules.find((rule) => rule.category === category);
    if (hard) {
      return actionForRule(
        hard.action,
        elapsedSeconds,
        hard.daily_minutes,
        "AGE_BAND_HARD_CATEGORY",
        hard.rule_id
      );
    }
  }

  if (category) {
    const defaultRule = bundle.base_policy.default_category_rules.find(
      (rule) => rule.category === category
    );
    if (defaultRule) {
      return actionForRule(
        defaultRule.action,
        elapsedSeconds,
        defaultRule.daily_minutes,
        "DEFAULT_CATEGORY_RULE",
        defaultRule.rule_id
      );
    }
  }

  if (target.kind === "APP") {
    const action = bundle.base_policy.unknown_app_policy === "BLOCK" ||
      bundle.base_policy.unknown_app_policy === "LIMIT_AND_NOTIFY"
      ? "BLOCK"
      : "ALLOW";
    return {
      action,
      reason_code: "UNKNOWN_APP_POLICY",
      policy_rule_id: null
    };
  }
  const action =
    bundle.base_policy.unknown_domain_policy === "BLOCK" ||
    bundle.base_policy.unknown_domain_policy === "BLOCK_WHILE_CLASSIFYING"
      ? "BLOCK"
      : "ALLOW";
  return { action, reason_code: "UNKNOWN_DOMAIN_POLICY", policy_rule_id: null };
}
