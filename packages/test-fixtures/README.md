# Cross-language policy fixtures

`policy-decision-cases.json` is the conformance contract. A runner loads the
named bundle from `bundles`, passes each case's `context` to its evaluator, and
compares the complete result with `expected`:

```text
{ action, reason_code, policy_rule_id, bundle_stale }
```

Timestamps are ISO-8601 instants. Schedule days use ISO weekday numbers
(`1 = Monday`, `7 = Sunday`) and local windows are interpreted in the bundle's
IANA timezone. Usage is an explicit device/app/category counter view supplied by
monotonic native accounting. The `tampered-signature` case represents the
verification gate before policy evaluation; it must reject the bundle and never
silently allow access. `rejected_bundles` contains schema-validation fragments
for the required fail-closed validation cases.
