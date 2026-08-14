import { describe, expect, it } from "vitest";
import { canonicalizeForSigning } from "./canonical.js";
import type { SignedPolicyBundle } from "./generated.js";

describe("policy signing canonicalization", () => {
  it("sorts object keys and excludes signature deterministically", () => {
    const first = {
      signature: "ignored",
      schema_version: 1,
      policy_version: 1,
      family_id: "family",
      child_profile_id: "child",
      issued_at: "2026-01-01T00:00:00Z",
      expires_soft_at: "2026-01-08T00:00:00Z",
      age_band: "TEEN",
      base_policy: {},
      app_rules: [],
      domain_rules: [],
      category_rules: [],
      routines: [],
      temporary_overrides: [],
      communication_safety: {},
    } as unknown as SignedPolicyBundle;
    const second = { ...first, signature: "different" };
    expect(new TextDecoder().decode(canonicalizeForSigning(first))).toBe(
      new TextDecoder().decode(canonicalizeForSigning(second))
    );
    expect(new TextDecoder().decode(canonicalizeForSigning(first))).not.toContain(
      "signature"
    );
  });
});
