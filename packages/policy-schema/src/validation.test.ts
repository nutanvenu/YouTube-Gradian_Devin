import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { BundleValidationError, validateBundle } from "./validation.js";
import type { SignedPolicyBundle } from "./generated.js";

const validBundle: SignedPolicyBundle = {
  schema_version: 1,
  policy_version: 1,
  family_id: "family",
  child_profile_id: "child",
  issued_at: "2026-01-01T00:00:00Z",
  expires_soft_at: "2026-01-08T00:00:00Z",
  key_id: "test-key",
  age_band: "TEEN",
  base_policy: {
    timezone: "UTC",
    unknown_domain_policy: "BLOCK",
    unknown_app_policy: "BLOCK",
    hard_category_rules: [],
    default_category_rules: [],
    safety_allowlist: []
  },
  app_rules: [],
  domain_rules: [],
  category_rules: [],
  routines: [],
  temporary_overrides: [],
  communication_safety: {
    enabled: false,
    severity_threshold: "HIGH",
    android_notification_signals: false,
    android_accessibility_signals: false
  },
  signature: "fixture"
};

const fixtureDocument = JSON.parse(
  readFileSync(
    resolve(process.cwd(), "packages/test-fixtures/policy-decision-cases.json"),
    "utf8"
  )
) as { rejected_bundles: Record<string, Record<string, unknown>> };

describe("policy bundle validation", () => {
  it.each(Object.entries(fixtureDocument.rejected_bundles))(
    "rejects fixture %s",
    (_description, patch) => {
      const candidate = { ...validBundle, ...patch };
      expect(() => {
        validateBundle(candidate);
      }).toThrow(BundleValidationError);
    }
  );

  it("rejects invalid timezone, domain IPs, single labels, and wildcards", () => {
    for (const domain of ["127.0.0.1", "localhost", "*.example.com"]) {
      const candidate = {
        ...validBundle,
        domain_rules: [{ rule_id: "domain", domain, action: "BLOCK" }]
      };
      expect(() => {
        validateBundle(candidate);
      }).toThrow(BundleValidationError);
    }
    expect(() => {
      validateBundle({
        ...validBundle,
        base_policy: { ...validBundle.base_policy, timezone: "Not/IANA" }
      });
    }).toThrow(BundleValidationError);
  });

  it("requires conditional rule fields and scheduled routine windows", () => {
    expect(() => {
      validateBundle({
        ...validBundle,
        app_rules: [{ rule_id: "limit", app_ref: "app", action: "LIMIT" }]
      });
    }).toThrow(BundleValidationError);
    expect(() => {
      validateBundle({
        ...validBundle,
        routines: [{ routine_id: "scheduled", name: "School", kind: "SCHEDULED" }]
      });
    }).toThrow(BundleValidationError);
  });

  it("rejects duplicate identifiers across all rule and routine collections", () => {
    expect(() => {
      validateBundle({
        ...validBundle,
        app_rules: [{ rule_id: "duplicate", app_ref: "app", action: "BLOCK" }],
        routines: [{ routine_id: "duplicate", name: "Routine", kind: "MANUAL" }]
      });
    }).toThrow(BundleValidationError);
  });
});
