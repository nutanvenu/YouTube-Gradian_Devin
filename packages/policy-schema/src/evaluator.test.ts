import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import type { PolicyDecision } from "@guardian/contracts";
import { evaluatePolicy, type DecisionContext } from "./evaluator.js";
import { tamperedSignatureDecision, unsafeTrustBundleForTesting } from "./signature.js";
import type { SignedPolicyBundle } from "./generated.js";

interface FixtureCase {
  id: string;
  description: string;
  bundle_ref: string;
  context: DecisionContext;
  expected: PolicyDecision;
}

interface FixtureDocument {
  bundles: Record<string, SignedPolicyBundle>;
  cases: FixtureCase[];
}

const fixtures = JSON.parse(
  readFileSync(
    resolve(process.cwd(), "packages/test-fixtures/policy-decision-cases.json"),
    "utf8"
  )
) as FixtureDocument;

function fixtureBundle(ref: string): SignedPolicyBundle {
  const bundle = fixtures.bundles[ref];
  if (!bundle) {
    throw new Error(`Missing policy fixture bundle: ${ref}`);
  }
  return bundle;
}

describe("policy decision conformance fixtures", () => {
  for (const fixture of fixtures.cases) {
    it(`${fixture.id}: ${fixture.description}`, () => {
      const bundle = fixtureBundle(fixture.bundle_ref);
      const result =
        fixture.id === "tampered-signature"
          ? tamperedSignatureDecision()
          : evaluatePolicy(unsafeTrustBundleForTesting(bundle), fixture.context);
      expect(result).toEqual(fixture.expected);
    });
  }
});

describe("policy evaluator invariants", () => {
  it("gives unknown apps a scoped limited-mode budget", () => {
    const bundle = unsafeTrustBundleForTesting(fixtureBundle("young"));
    expect(
      evaluatePolicy(bundle, {
        target: { kind: "APP", ref: "com.unknown.app" },
        timestamp: "2026-01-05T12:00:00Z",
        usage: {
          device_seconds_today: 0,
          app_seconds_today: { "com.unknown.app": 0 },
          category_seconds_today: {}
        }
      })
    ).toMatchObject({
      action: "ALLOW_WITH_BUDGET",
      reason_code: "UNKNOWN_APP_BUDGET_AVAILABLE"
    });
  });

  it("exhausts the unknown-app limited-mode budget independently", () => {
    const bundle = unsafeTrustBundleForTesting(fixtureBundle("young"));
    expect(
      evaluatePolicy(bundle, {
        target: { kind: "APP", ref: "com.unknown.app" },
        timestamp: "2026-01-05T08:00:00Z",
        usage: {
          device_seconds_today: 0,
          app_seconds_today: { "com.unknown.app": 1800 },
          category_seconds_today: {}
        }
      })
    ).toMatchObject({
      action: "LIMIT_REACHED",
      reason_code: "UNKNOWN_APP_BUDGET_EXHAUSTED"
    });
  });

  it("is deterministic for the same bundle and context", () => {
    const bundle = unsafeTrustBundleForTesting(fixtureBundle("precedence"));
    fc.assert(
      fc.property(
        fc.constantFrom("APP", "DOMAIN", "CATEGORY"),
        fc.string({ minLength: 1 }),
        fc.integer({ min: 0, max: 86_400 }),
        (kind, ref, elapsed) => {
          const context: DecisionContext = {
            target: { kind, ref },
            timestamp: "2026-01-05T20:00:00Z",
            usage: {
              device_seconds_today: elapsed,
              app_seconds_today: { [ref]: elapsed },
              category_seconds_today: {}
            }
          };
          const first = evaluatePolicy(bundle, context);
          const second = evaluatePolicy(bundle, context);
          expect(second).toEqual(first);
        }
      )
    );
  });

  it("always returns a closed decision action for arbitrary target inputs", () => {
    const bundle = unsafeTrustBundleForTesting(fixtureBundle("precedence"));
    fc.assert(
      fc.property(
        fc.constantFrom("APP", "DOMAIN", "CATEGORY"),
        fc.string({ minLength: 1 }),
        fc.integer({ min: 0, max: 86_400 }),
        (kind, ref, elapsed) => {
          const result = evaluatePolicy(bundle, {
            target: { kind, ref },
            timestamp: "2026-01-05T20:00:00Z",
            usage: {
              device_seconds_today: elapsed,
              app_seconds_today: { [ref]: elapsed },
              category_seconds_today: {}
            }
          });
          expect(["ALLOW", "BLOCK", "LIMIT_REACHED", "ALLOW_WITH_BUDGET"]).toContain(
            result.action
          );
          expect(result.reason_code).toBeTruthy();
        }
      )
    );
  });
});
