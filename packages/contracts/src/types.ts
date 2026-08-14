export const AGE_BANDS = ["YOUNG_CHILD", "PRETEEN", "TEEN", "OLDER_TEEN"] as const;
export type AgeBand = (typeof AGE_BANDS)[number];

export const CAPABILITY_LEVELS = [
  "FULL",
  "BEST_EFFORT",
  "UNAVAILABLE",
  "REGION_LIMITED"
] as const;
export type CapabilityLevel = (typeof CAPABILITY_LEVELS)[number];

export interface CapabilityStatus {
  level: CapabilityLevel;
  detail: string | null;
  updatedAt: string;
}

export type CapabilityRecord = Record<string, CapabilityStatus>;

export interface Parent {
  id: string;
  email: string;
  displayName: string;
  createdAt: string;
}

export interface Family {
  id: string;
  name: string;
  ownerParentId: string;
  createdAt: string;
}

export interface ChildProfile {
  id: string;
  familyId: string;
  displayName: string;
  age: number;
  ageBand: AgeBand;
  timezone: string;
  createdAt: string;
}

export type DevicePlatform = "ANDROID" | "IOS";

export interface Device {
  id: string;
  childProfileId: string;
  platform: DevicePlatform;
  platformDeviceId: string;
  capabilities: CapabilityRecord;
  lastSeenAt: string | null;
}

export type ProtectionHealth = "HEALTHY" | "DEGRADED" | "DISABLED" | "UNKNOWN";
export type ProtectionStatus = {
  active: boolean;
  health: ProtectionHealth;
  policyVersion: number | null;
  observedAt: string;
  details: string | null;
};

export type RequestState =
  | "PENDING"
  | "APPROVED"
  | "DENIED"
  | "EXPIRED"
  | "CANCELLED";

export interface AccessRequest {
  id: string;
  childProfileId: string;
  targetRef: string;
  requestedMinutes: number | null;
  state: RequestState;
  createdAt: string;
  resolvedAt: string | null;
}

export type PolicyDecisionAction =
  | "ALLOW"
  | "BLOCK"
  | "LIMIT_REACHED"
  | "ALLOW_WITH_BUDGET";

export type PolicyReasonCode =
  | "SAFETY_ALLOWLIST"
  | "TEMPORARY_PARENT_OVERRIDE"
  | "MANUAL_ROUTINE"
  | "SCHEDULED_ROUTINE"
  | "EXPLICIT_TARGET_RULE"
  | "AGE_BAND_HARD_CATEGORY"
  | "DEFAULT_CATEGORY_RULE"
  | "UNKNOWN_APP_POLICY"
  | "UNKNOWN_DOMAIN_POLICY"
  | "BUDGET_AVAILABLE"
  | "BUDGET_EXHAUSTED"
  | "SCHEDULE_OUTSIDE_WINDOW"
  | "TEMPORARY_OVERRIDE_EXPIRED"
  | "SOFT_EXPIRED_BUNDLE"
  | "TAMPERED_SIGNATURE";

export interface PolicyDecision {
  action: PolicyDecisionAction;
  reason_code: PolicyReasonCode;
  policy_rule_id: string | null;
}

export interface TimeRange {
  start: string;
  end: string;
}

export interface UsageSummary {
  range: TimeRange;
  totalSeconds: number;
  byTarget: Record<string, number>;
}

export interface ObservedApp {
  platformAppId: string;
  displayName: string;
  category: string;
  observedAt: string;
}

export type PermissionResult =
  | { granted: true }
  | { granted: false; reason: string };

export type ApplyResult =
  | { applied: true; policyVersion: number }
  | { applied: false; policyVersion: number | null; reason: string };

export interface GuardianProtectionNative {
  getCapabilities(): Promise<CapabilityRecord>;
  getProtectionStatus(): Promise<ProtectionStatus>;
  requestVpnPermission(): Promise<PermissionResult>;
  openUsageAccessSettings(): Promise<void>;
  openAccessibilitySettings(): Promise<void>;
  openNotificationAccessSettings(): Promise<void>;
  startProtection(): Promise<void>;
  applyPolicyBundle(bundle: unknown): Promise<ApplyResult>;
  getUsageSummary(range: TimeRange): Promise<UsageSummary>;
  getObservedApps(): Promise<ObservedApp[]>;
  subscribe(listener: (event: GuardianNativeEvent) => void): { remove: () => void };
}

export type GuardianNativeEvent =
  | { type: "PROTECTION_STATUS_CHANGED"; status: ProtectionStatus }
  | { type: "APP_BLOCKED"; appRef: string; reasonCode: PolicyReasonCode }
  | {
      type: "WEB_BLOCKED";
      domain?: string;
      category?: string;
      reasonCode: PolicyReasonCode;
    }
  | { type: "TIME_WARNING"; targetRef: string; remainingSeconds: number }
  | { type: "TIME_EXPIRED"; targetRef: string }
  | { type: "SAFETY_EVENT"; category: string; severity: string }
  | { type: "POLICY_APPLIED"; version: number }
  | { type: "PERMISSION_STATE_CHANGED"; capability: string; state: string };

export type ApiErrorCode =
  | "VALIDATION_ERROR"
  | "UNAUTHENTICATED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "CONFLICT"
  | "POLICY_VERSION_CONFLICT"
  | "RATE_LIMITED"
  | "INTERNAL_ERROR";

export interface ApiError {
  error: {
    code: ApiErrorCode;
    message: string;
    retryable: boolean;
    details: Record<string, unknown>;
  };
}

export function isAgeBand(value: unknown): value is AgeBand {
  return typeof value === "string" && (AGE_BANDS as readonly string[]).includes(value);
}

export function isCapabilityLevel(value: unknown): value is CapabilityLevel {
  return (
    typeof value === "string" &&
    (CAPABILITY_LEVELS as readonly string[]).includes(value)
  );
}

export function isPolicyDecisionAction(value: unknown): value is PolicyDecisionAction {
  return (
    value === "ALLOW" ||
    value === "BLOCK" ||
    value === "LIMIT_REACHED" ||
    value === "ALLOW_WITH_BUDGET"
  );
}
