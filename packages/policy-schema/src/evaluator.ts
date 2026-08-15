import { Temporal } from "@js-temporal/polyfill";
import { getDomain, getPublicSuffix } from "tldts";
import type {
  PolicyDecision,
  PolicyDecisionAction,
  PolicyReasonCode,
  UsageView
} from "@guardian/contracts";
import type {
  AppRule,
  Category,
  CategoryRule,
  DomainRule,
  Routine,
  TemporaryOverride
} from "./generated.js";
import type { VerifiedPolicyBundle } from "./signature.js";

export interface DecisionContext {
  target:
    | { kind: "APP"; ref: string; category?: Category }
    | { kind: "DOMAIN"; ref: string; category?: Category }
    | { kind: "CATEGORY"; ref: string; category?: Category };
  timestamp: string;
  timezone?: string;
  usage: UsageView;
  current_manual_routine_id?: string;
  reputation_verdict?: "KNOWN_SAFE" | "KNOWN_RISK" | "UNKNOWN";
}

interface Candidate {
  action: PolicyDecisionAction;
  reason_code: PolicyReasonCode;
  policy_rule_id: string | null;
  budget_exempt: boolean;
}

type RuleLike = AppRule | CategoryRule | DomainRule | TemporaryOverride;

function localDateTime(timestamp: string, timezone: string): Temporal.ZonedDateTime {
  return Temporal.Instant.from(timestamp).toZonedDateTimeISO(timezone);
}

function minutesSinceMidnight(value: string): number {
  const [hoursText, minutesText] = value.split(":");
  return Number(hoursText) * 60 + Number(minutesText);
}

export function isInWindow(
  window: { days: number[]; start: string; end: string },
  dateTime: Temporal.ZonedDateTime
): boolean {
  const today = dateTime.dayOfWeek;
  const yesterday = today === 1 ? 7 : today - 1;
  const current = dateTime.hour * 60 + dateTime.minute;
  const start = minutesSinceMidnight(window.start);
  const end = minutesSinceMidnight(window.end);
  if (start === end) return window.days.includes(today);
  if (start < end) {
    return window.days.includes(today) && current >= start && current < end;
  }
  return (
    (window.days.includes(today) && current >= start) ||
    (window.days.includes(yesterday) && current < end)
  );
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
  if (
    !getDomain(configured) ||
    !getPublicSuffix(configured) ||
    configured === getPublicSuffix(configured)
  ) {
    return false;
  }
  return rule.match === "EXACT"
    ? candidate === configured
    : candidate === configured || candidate.endsWith(`.${configured}`);
}

function lastMatching<T>(items: T[], predicate: (item: T) => boolean): T | undefined {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const item = items[index];
    if (item !== undefined && predicate(item)) return item;
  }
  return undefined;
}

function mostSpecificDomainRule(
  rules: DomainRule[],
  target: string,
): DomainRule | undefined {
  const candidate = normalizedDomain(target);
  if (!candidate) return undefined;
  let selected: DomainRule | undefined;
  let selectedSpecificity = -1;
  for (const rule of rules) {
    if (!domainMatches(rule, candidate)) continue;
    const configured = normalizedDomain(rule.domain);
    const specificity = configured.length + (rule.match === "SUBDOMAINS" ? 2 : 0);
    if (specificity >= selectedSpecificity) {
      selected = rule;
      selectedSpecificity = specificity;
    }
  }
  return selected;
}

function categoryForTarget(
  target: DecisionContext["target"]
): Category | undefined {
  return target.category ?? (target.kind === "CATEGORY" ? target.ref as Category : undefined);
}

function usageSecondsForTarget(
  target: DecisionContext["target"],
  usage: UsageView
): number {
  if (target.kind === "APP") return usage.app_seconds_today[target.ref] ?? 0;
  const category = categoryForTarget(target);
  return category === undefined ? 0 : usage.category_seconds_today[category] ?? 0;
}

function actionForRule(
  rule: RuleLike,
  usageSeconds: number,
  reason: PolicyReasonCode,
  budgetExempt: boolean
): Candidate {
  if (rule.action === "BLOCK") {
    return { action: "BLOCK", reason_code: reason, policy_rule_id: rule.rule_id, budget_exempt: budgetExempt };
  }
  if (rule.action === "ASK_PARENT") {
    return {
      action: "BLOCK",
      reason_code: "REQUIRES_PARENT_APPROVAL",
      policy_rule_id: rule.rule_id,
      budget_exempt: budgetExempt
    };
  }
  if (rule.action === "LIMIT") {
    const exhausted = usageSeconds >= (rule.daily_minutes ?? 0) * 60;
    return {
      action: exhausted
        ? "LIMIT_REACHED"
        : reason === "TEMPORARY_PARENT_OVERRIDE"
          ? "ALLOW"
          : "ALLOW_WITH_BUDGET",
      reason_code: exhausted
        ? "BUDGET_EXHAUSTED"
        : reason === "TEMPORARY_PARENT_OVERRIDE"
          ? "TEMPORARY_PARENT_OVERRIDE"
          : "BUDGET_AVAILABLE",
      policy_rule_id: rule.rule_id,
      budget_exempt: budgetExempt
    };
  }
  return {
    action: "ALLOW",
    reason_code: reason,
    policy_rule_id: rule.rule_id,
    budget_exempt: budgetExempt || rule.action === "UNLIMITED"
  };
}

function candidateDecision(
  candidate: Candidate,
  bundle: VerifiedPolicyBundle,
  context: DecisionContext,
  stale: boolean
): PolicyDecision {
  const activeDeviceOverride = bundle.temporary_overrides.find(
    (override) =>
      override.target_kind === "DEVICE" &&
      Temporal.Instant.compare(
        Temporal.Instant.from(context.timestamp),
        Temporal.Instant.from(override.starts_at)
      ) >= 0 &&
      Temporal.Instant.compare(
        Temporal.Instant.from(context.timestamp),
        Temporal.Instant.from(override.expires_at)
      ) < 0
  );
  const deviceBudgets = [
    bundle.base_policy.daily_device_budget_minutes,
    activeDeviceOverride?.daily_minutes
  ].filter((value): value is number => value !== undefined);
  const deviceBudget = deviceBudgets.length > 0 ? Math.max(...deviceBudgets) : undefined;
  if (
    deviceBudget !== undefined &&
    context.usage.device_seconds_today >= deviceBudget * 60 &&
    !candidate.budget_exempt &&
    (candidate.action === "ALLOW" || candidate.action === "ALLOW_WITH_BUDGET")
  ) {
    return {
      action: "LIMIT_REACHED",
      reason_code: "DEVICE_BUDGET_EXHAUSTED",
      policy_rule_id: candidate.policy_rule_id,
      bundle_stale: stale
    };
  }
  return {
    action: candidate.action,
    reason_code: candidate.reason_code,
    policy_rule_id: candidate.policy_rule_id,
    bundle_stale: stale
  };
}

function routineCandidate(
  routine: Routine,
  context: DecisionContext,
  reason: PolicyReasonCode
): Candidate | null {
  if (
    routine.kind === "SCHEDULED" &&
    (!routine.window ||
      !isInWindow(
        routine.window,
        localDateTime(context.timestamp, context.timezone ?? "UTC")
      ))
  ) {
    return null;
  }
  const target = context.target;
  const category = categoryForTarget(target);
  if (target.kind === "APP" && routine.blocked_apps?.includes(target.ref)) {
    return { action: "BLOCK", reason_code: reason, policy_rule_id: routine.routine_id, budget_exempt: false };
  }
  if (target.kind === "APP" && routine.allowed_apps?.includes(target.ref)) {
    return { action: "ALLOW", reason_code: reason, policy_rule_id: routine.routine_id, budget_exempt: false };
  }
  if (category && routine.blocked_categories?.includes(category)) {
    return { action: "BLOCK", reason_code: reason, policy_rule_id: routine.routine_id, budget_exempt: false };
  }
  if (category && routine.allowed_categories?.includes(category)) {
    return { action: "ALLOW", reason_code: reason, policy_rule_id: routine.routine_id, budget_exempt: false };
  }
  if (routine.web_mode === "STRICT" && target.kind === "DOMAIN") {
    return { action: "BLOCK", reason_code: reason, policy_rule_id: routine.routine_id, budget_exempt: false };
  }
  return null;
}

function overrideMatches(
  override: TemporaryOverride,
  context: DecisionContext
): boolean {
  const exactMatch =
    override.target_kind === context.target.kind &&
    override.target_ref === context.target.ref;
  const categoryMatch =
    override.target_kind === "CATEGORY" &&
    override.target_ref === context.target.category;
  return exactMatch || categoryMatch;
}

function staleAt(timestamp: string, expiresSoftAt: string): boolean {
  return Temporal.Instant.compare(
    Temporal.Instant.from(timestamp),
    Temporal.Instant.from(expiresSoftAt)
  ) >= 0;
}

export function evaluatePolicy(
  bundle: VerifiedPolicyBundle,
  context: DecisionContext
): PolicyDecision {
  const timezone = context.timezone ?? bundle.base_policy.timezone;
  const target = context.target;
  const usageSeconds = usageSecondsForTarget(target, context.usage);
  const stale = staleAt(context.timestamp, bundle.expires_soft_at);
  const routineContext =
    context.timezone === undefined
      ? { ...context, timezone: bundle.base_policy.timezone }
      : context;

  const safety = bundle.base_policy.safety_allowlist.find(
    (entry) =>
      entry.target_kind === target.kind && entry.target_ref === target.ref
  );
  if (safety) {
    return candidateDecision(
      { action: "ALLOW", reason_code: "SAFETY_ALLOWLIST", policy_rule_id: null, budget_exempt: true },
      bundle,
      context,
      stale
    );
  }

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
    return candidateDecision(
      actionForRule(activeOverride, usageSeconds, "TEMPORARY_PARENT_OVERRIDE", true),
      bundle,
      context,
      stale
    );
  }

  const manual = context.current_manual_routine_id
    ? bundle.routines.find(
        (routine) =>
          routine.kind === "MANUAL" &&
          routine.routine_id === context.current_manual_routine_id
      )
    : undefined;
  const manualResult = manual
    ? routineCandidate(manual, routineContext, "MANUAL_ROUTINE")
    : null;
  if (manualResult) return candidateDecision(manualResult, bundle, context, stale);

  const scheduled = bundle.routines
    .filter((routine) => routine.kind === "SCHEDULED")
    .map((routine) => routineCandidate(routine, routineContext, "SCHEDULED_ROUTINE"))
    .find((candidate): candidate is Candidate => candidate !== null);
  if (scheduled) return candidateDecision(scheduled, bundle, context, stale);

  const explicit =
    target.kind === "APP"
      ? lastMatching(bundle.app_rules, (rule) => rule.app_ref === target.ref)
      : target.kind === "DOMAIN"
        ? mostSpecificDomainRule(bundle.domain_rules, target.ref)
        : lastMatching(
            bundle.category_rules,
            (rule) => rule.category === categoryForTarget(target)
          );
  if (explicit) {
    if (
      explicit.schedule &&
      !isInWindow(explicit.schedule, localDateTime(context.timestamp, timezone))
    ) {
      return candidateDecision(
        {
          action: "BLOCK",
          reason_code: "SCHEDULE_OUTSIDE_WINDOW",
          policy_rule_id: explicit.rule_id,
          budget_exempt: false
        },
        bundle,
        context,
        stale
      );
    }
    return candidateDecision(
      actionForRule(
        explicit,
        usageSeconds,
        "EXPLICIT_TARGET_RULE",
        explicit.exclude_from_budget === true
      ),
      bundle,
      context,
      stale
    );
  }

  const category = categoryForTarget(target);
  if (category) {
    const hard = bundle.base_policy.hard_category_rules.find(
      (rule) => rule.category === category
    );
    if (hard) {
      return candidateDecision(
        actionForRule(
          hard,
          usageSeconds,
          "AGE_BAND_HARD_CATEGORY",
          hard.exclude_from_budget === true
        ),
        bundle,
        context,
        stale
      );
    }
    const defaultRule = bundle.base_policy.default_category_rules.find(
      (rule) => rule.category === category
    );
    if (defaultRule) {
      return candidateDecision(
        actionForRule(
          defaultRule,
          usageSeconds,
          "DEFAULT_CATEGORY_RULE",
          defaultRule.exclude_from_budget === true
        ),
        bundle,
        context,
        stale
      );
    }
  }

  if (
    target.kind === "APP" &&
    bundle.base_policy.unknown_app_policy === "LIMIT_AND_NOTIFY"
  ) {
    const exhausted =
      usageSeconds >= (bundle.base_policy.unknown_app_daily_minutes ?? 0) * 60;
    return candidateDecision(
      {
        action: exhausted ? "LIMIT_REACHED" : "ALLOW_WITH_BUDGET",
        reason_code: exhausted
          ? "UNKNOWN_APP_BUDGET_EXHAUSTED"
          : "UNKNOWN_APP_BUDGET_AVAILABLE",
        policy_rule_id: null,
        budget_exempt: false
      },
      bundle,
      context,
      stale
    );
  }
  const action =
    target.kind === "APP"
      ? bundle.base_policy.unknown_app_policy === "BLOCK"
        ? "BLOCK"
        : "ALLOW"
      : bundle.base_policy.unknown_domain_policy === "BLOCK" ||
          bundle.base_policy.unknown_domain_policy === "BLOCK_WHILE_CLASSIFYING"
        ? "BLOCK"
        : "ALLOW";
  return candidateDecision(
    {
      action,
      reason_code:
        target.kind === "APP" ? "UNKNOWN_APP_POLICY" : "UNKNOWN_DOMAIN_POLICY",
      policy_rule_id: null,
      budget_exempt: false
    },
    bundle,
    context,
    stale
  );
}
