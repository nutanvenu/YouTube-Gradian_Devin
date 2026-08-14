# Cross-language policy fixtures

`policy-decision-cases.json` is the conformance contract. A runner loads the
named bundle from `bundles`, passes each case's `context` to its evaluator, and
compares the complete result with `expected`:

```text
{ action, reason_code, policy_rule_id }
```

Timestamps are ISO-8601 instants. Schedule days use ISO weekday numbers
(`1 = Monday`, `7 = Sunday`) and local windows are interpreted in the bundle's
IANA timezone. A case with `context.signature_valid = false` represents the
verification gate before policy evaluation; it must reject the bundle and never
silently allow access.
