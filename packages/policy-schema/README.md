# Guardian policy schema

`schema/policy-bundle.schema.json` is the canonical signed bundle contract. Its
top-level envelope is intentionally fixed to the fields in PRD §12.1:

`schema_version`, `policy_version`, `family_id`, `child_profile_id`, `issued_at`,
`expires_soft_at`, `age_band`, `base_policy`, `app_rules`, `domain_rules`,
`category_rules`, `routines`, `temporary_overrides`, `communication_safety`, and
`signature`.

## Verification, validation, and signature bytes

Callers must follow `verifyBundle` → `validateBundle` → compile/evaluate. The
evaluator accepts only a branded verified bundle; `unsafeTrustBundleForTesting`
is the explicitly named test-only escape hatch. The backend owns the Ed25519
private key; clients only verify.

The signature covers the bundle with `signature` removed. Serialize the remaining
JSON value using the JSON Canonicalization Scheme (JCS) shape:

- object keys sorted by their UTF-16 code units;
- arrays retain their input order;
- strings use JSON escaping;
- no insignificant whitespace or trailing newline.

Integer-only numerics are a deliberate signing constraint. Non-integer and
non-finite numbers, `undefined`, and strings containing lone UTF-16 surrogates
are rejected rather than serialized ambiguously. The resulting UTF-8 bytes are
signed and verified with Ed25519. `canonicalizeForSigning` is the reference
implementation so Python, Kotlin, and Swift can reproduce it.

## Time and matching

Schedules use the child's IANA timezone and ISO-8601 instants. `days` identifies
the local day on which a window starts. Thus `days: [6]`, `21:00`–`07:00`
matches Saturday night and Sunday morning. `start === end` means a full 24-hour
window on each selected start day. The evaluator uses the maintained
`@js-temporal/polyfill` package for timezone/DST conversion and `tldts` for
public-suffix-aware domain matching.

Usage is supplied by native monotonic accounting as separate device, app, and
category counters. The evaluator never derives usage from wall-clock timestamps,
so a clock rollback cannot resurrect an exhausted budget. Soft expiry is
informational: `PolicyDecision.bundle_stale` reports stale state while
enforcement and precedence remain unchanged.

When `unknown_app_policy` is `LIMIT_AND_NOTIFY`, `unknown_app_daily_minutes`
defines a per-application limited-mode budget. The evaluator returns
`ALLOW_WITH_BUDGET` or `LIMIT_REACHED` with dedicated unknown-app budget
reason codes; it does not collapse this posture into a block.

Configured IP literals, single-label hosts, and wildcard domains are rejected
by `validateBundle`; invalid runtime targets simply do not match a rule. A
configured public suffix such as `co.uk` is not allowed to shadow
`evil.co.uk`.
