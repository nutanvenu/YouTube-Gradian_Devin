# Guardian policy schema

`schema/policy-bundle.schema.json` is the canonical signed bundle contract. Its
top-level envelope is intentionally fixed to the fields in PRD §12.1:

`schema_version`, `policy_version`, `family_id`, `child_profile_id`, `issued_at`,
`expires_soft_at`, `age_band`, `base_policy`, `app_rules`, `domain_rules`,
`category_rules`, `routines`, `temporary_overrides`, `communication_safety`, and
`signature`.

## Signature bytes

The signature covers the bundle with `signature` removed. Serialize the remaining
JSON value using the JSON Canonicalization Scheme (JCS) shape:

- object keys sorted by their UTF-16 code units;
- arrays retain their input order;
- strings use JSON escaping;
- numbers use ECMAScript JSON number serialization;
- no insignificant whitespace or trailing newline.

The resulting UTF-8 bytes are signed and verified with Ed25519. The backend owns
the private key; clients only verify. `canonicalizeForSigning` is the reference
implementation and is deliberately dependency-free so Python, Kotlin, and Swift
can reproduce it.

## Time and matching

Schedules use the child's IANA timezone and ISO-8601 instants. The evaluator uses
the maintained `@js-temporal/polyfill` package for timezone/DST conversion and
`tldts` for public-suffix-aware domain matching. A domain rule on a public suffix
such as `co.uk` is never treated as a valid parent of `evil.co.uk`.
