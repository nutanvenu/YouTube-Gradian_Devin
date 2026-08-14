import { describe, expect, it } from "vitest";
import { canonicalizeForSigning } from "./canonical.js";
import type { SignedPolicyBundle } from "./generated.js";
import fixture from "../test-fixtures/canonical-cross-language.json" with { type: "json" };

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
      key_id: "test-key",
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

  it.each([
    ["fractional", 1.5],
    ["nan", Number.NaN],
    ["infinity", Number.POSITIVE_INFINITY]
  ])("rejects %s numbers", (_name, value) => {
    expect(() => canonicalizeForSigning({ ...({} as SignedPolicyBundle), policy_version: value })).toThrow();
  });

  it("rejects undefined and lone surrogates", () => {
    expect(() =>
      canonicalizeForSigning({
        ...({} as SignedPolicyBundle),
        family_id: undefined
      } as unknown as SignedPolicyBundle)
    ).toThrow();
    expect(() =>
      canonicalizeForSigning({ ...({} as SignedPolicyBundle), family_id: "\ud800" })
    ).toThrow();
  });

  it("matches the shared cross-language canonicalization fixture", () => {
    const bytes = canonicalizeForSigning(fixture.value as unknown as SignedPolicyBundle);
    expect(Buffer.from(bytes).toString("base64")).toBe(fixture.canonical_utf8_base64);
  });
});
