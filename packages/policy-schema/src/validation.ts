import Ajv2020, { type ErrorObject, type ValidateFunction } from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { isIP } from "node:net";
import { Temporal } from "@js-temporal/polyfill";
import { HARD_CATEGORIES } from "@guardian/contracts";
import schema from "../schema/policy-bundle.schema.json" with { type: "json" };
import type { SignedPolicyBundle } from "./generated.js";

const SUPPORTED_SCHEMA_VERSION = 1;
const ajv = new Ajv2020.default({
  allErrors: true,
  strict: true,
  strictRequired: false
});
addFormats.default(ajv);
const validateSchema: ValidateFunction<SignedPolicyBundle> = ajv.compile(schema);

export class BundleValidationError extends Error {
  readonly issues: readonly string[];

  constructor(issues: readonly string[]) {
    super(`Policy bundle validation failed: ${issues.join("; ")}`);
    this.name = "BundleValidationError";
    this.issues = issues;
  }
}

function issueText(error: ErrorObject): string {
  return `${error.instancePath || "/"} ${error.message ?? "is invalid"}`;
}

function validateTimezone(timezone: string): boolean {
  try {
    Temporal.Instant.from("2026-01-01T00:00:00Z").toZonedDateTimeISO(timezone);
    return true;
  } catch {
    return false;
  }
}

function validateDomains(bundle: SignedPolicyBundle, issues: string[]): void {
  for (const [index, rule] of bundle.domain_rules.entries()) {
    const domain = rule.domain.trim().replace(/\.$/, "");
    if (isIP(domain) !== 0 || !domain.includes(".")) {
      issues.push(
        `/domain_rules/${String(index)}/domain must be a non-IP registrable host`
      );
    }
  }
}

function validateUniqueIdentifiers(
  bundle: SignedPolicyBundle,
  issues: string[]
): void {
  const identifiers = new Set<string>();
  const collections = [
    ...bundle.app_rules,
    ...bundle.domain_rules,
    ...bundle.category_rules,
    ...bundle.base_policy.hard_category_rules,
    ...bundle.base_policy.default_category_rules,
    ...bundle.routines,
    ...bundle.temporary_overrides
  ];
  for (const rule of collections) {
    const identifier = "rule_id" in rule ? rule.rule_id : rule.routine_id;
    if (identifiers.has(identifier)) {
      issues.push(`/identifiers/${identifier} must be unique across the bundle`);
    }
    identifiers.add(identifier);
  }
}

export function validateBundle(value: unknown): asserts value is SignedPolicyBundle {
  const issues: string[] = [];
  if (
    typeof value !== "object" ||
    value === null ||
    !("schema_version" in value) ||
    value.schema_version !== SUPPORTED_SCHEMA_VERSION
  ) {
    issues.push(
      `/schema_version must be supported version ${String(SUPPORTED_SCHEMA_VERSION)}`
    );
  }
  if (!validateSchema(value)) {
    issues.push(...(validateSchema.errors ?? []).map(issueText));
  }
  if (validateSchema(value)) {
    const bundle = value;
    if (!validateTimezone(bundle.base_policy.timezone)) {
      issues.push("/base_policy/timezone must resolve as an IANA timezone");
    }
    for (const [index, rule] of bundle.base_policy.hard_category_rules.entries()) {
      if (!(HARD_CATEGORIES as readonly string[]).includes(rule.category)) {
        issues.push(
          `/base_policy/hard_category_rules/${String(index)}/category is not hard`
        );
      }
    }
    validateDomains(bundle, issues);
    validateUniqueIdentifiers(bundle, issues);
  }
  if (issues.length > 0) throw new BundleValidationError(issues);
}
