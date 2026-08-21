# Task 1 — Family lifecycle and release-configuration closure

## Status

Implemented and locally validated to the extent supported by this host. This
change deliberately does not build an APK, deploy, create secrets, push, or
open a pull request.

## Changed behavior

- A parent sign-in now discovers an already-created family and its selected
  child before presenting setup. A parent can switch the selected child, add a
  child to an existing family, and all supported parent routes retain that
  child selection.
- The parent home inventory is now server-owned for the selected child rather
  than being inferred from the parent phone's local Guardian module. Activity,
  usage, requests, health, reports, rules, controls, and their detail routes
  pass the selected child through to the API/query cache.
- The server accepts an optional `child_id` for family activity, usage, health,
  and access-request lists, so one child's data is not mixed into another
  child's parent view. A regression test creates two paired children and
  verifies the selected-child filters.
- QR pairing is parsed as a URI rather than by query-string order. Valid
  `guardian://pair/session` QR payloads work whether `code` or `child_id`
  appears first; malformed payloads are rejected.
- Parent sign-out sends the refresh token to the backend logout endpoint,
  then always clears only parent credentials. A revoked child device now stops
  protection, clears native persisted child/policy/content identity and local
  device/role state, then returns to pairing; parent credentials remain out of
  scope for that recovery path.
- Android trusted policy keys, active policy key ID, and DoH URL can now be
  supplied only by environment variables at native build time. They no longer
  accept Gradle project properties. Native policy reset also removes persisted
  child identity and related policy/content state.

## Files changed

- Mobile family/session/API/UI: `apps/mobile/src/auth/session.tsx`,
  `apps/mobile/src/api/client.ts`, and the parent/child route screens under
  `apps/mobile/src/app/`.
- Mobile regressions and helper units: `apps/mobile/src/auth/session.test.tsx`,
  `apps/mobile/src/api/client.test.ts`, `apps/mobile/src/screens.test.tsx`,
  `apps/mobile/src/new-routes.test.tsx`,
  `apps/mobile/src/state/pairing-uri.{ts,test.ts}`, and
  `apps/mobile/src/state/child-device-recovery.{ts,test.ts}`.
- Backend selected-child API filtering and regression coverage:
  `backend/app/events/router.py`, `backend/app/families/router.py`,
  `backend/app/requests/router.py`, and
  `backend/tests/test_selected_child_filters.py`.
- Native bridge/reset and release binding: `packages/contracts/src/types.ts`,
  `apps/mobile/modules/guardian-protection/src/index.ts`, its Android Gradle,
  module, policy-manager, and encrypted-store sources, plus
  `apps/mobile/scripts/release-admission.test.mjs`.

## Validation

Passed:

```sh
corepack pnpm --filter guardian-mobile exec jest --runInBand
# 11 suites passed, 71 tests passed

corepack pnpm --filter guardian-mobile lint
# passed

corepack pnpm --filter guardian-mobile typecheck
# passed

corepack pnpm test
# 6 files passed, 67 tests passed

python3 -m compileall -q backend/app backend/tests
# passed

git diff --check
# passed
```

## Concerns and limits

- The host has no `java` executable, so Android Gradle/native release-admission
  execution and an Android build were not possible. No APK build was attempted
  by design.
- The host has no `uv` executable, so the backend pytest environment and
  OpenAPI client regeneration could not be run here. The mobile API calls use
  the already-supported query-string transport; the generated client schema
  should be regenerated and its diff reviewed in a provisioned backend
  environment.
- The host is Node `v24.19.0`; the repository declares Node `22.13.0`. All
  JavaScript checks above passed, but final release validation should repeat on
  the pinned runtime.
- The selected-child route propagation is implemented for the Task 1 parent
  screens. Any future parent screen that consumes child-scoped data must keep
  forwarding `childId`; this change does not introduce a global route guard to
  enforce that convention.

## Business intent and what this unlocks

Families can now return to an existing setup, deliberately choose the child
they are managing, add another child without duplicating a family, and recover
a revoked child phone into a clean re-pair flow. This unlocks a credible
multi-child consumer lifecycle while preventing one child's monitoring data
from being presented as another's. The environment-only native binding removes
a common release misconfiguration path and makes the intended signed-policy
trust configuration auditable before native release work.
