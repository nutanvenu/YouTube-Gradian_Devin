# Devin Checkpoint

## Current phase

Phase 1, Slice 1.7 in progress: Android VPN/TUN and web-domain enforcement.

The repository is on local `main`. No GitHub remote is configured and no PR has
been created or pushed.

## Fully complete and verified

### Backend and identity foundations

The backend identity, family, child-profile, pairing, signed-policy, device
credential, request, policy mutation, health, push-token, and authenticated
WebSocket foundations are implemented. Backend verification previously passed:

```text
ruff check app alembic tests
All checks passed!

mypy app
Success: no issues found in 50 source files

pytest -q
90 passed in 7.51s
```

The backend route registration is split into domain routers and
`backend/app/api/routes.py` and `handler_registry.py` have been removed.
`backend/app/api/route_handlers.py` still contains shared route
implementations and is a known extraction gap.

### Mobile foundation

Expo SDK 57, Expo Router, New Architecture, `expo-dev-client`, SecureStore
credentials, TanStack Query, real authentication/pairing flows, design-system
state components, and committed Android/iOS native projects are present.
The moved local module is discovered by Expo autolinking:

```text
Using expo modules
  - guardian-protection (0.1.0)
```

Real emulator evidence exists for parent signup, family and child creation,
pairing redemption, parent Home, child My Time, backend outage error/retry,
explicit revoked-device state, and standalone offline state:

```text
.scratch/emulator/04-child-my-time.png
.scratch/emulator/05-offline.png
.scratch/emulator/07-revoked-device.png
.scratch/emulator/09-standalone-offline-settled.png
.scratch/emulator/15-revoked-cleartext.png
```

The standalone offline screenshot showed:

```text
My time
You're offline. Last-known data may be shown.
```

The revoked-device screenshot showed:

```text
Protection removed
This device is no longer linked to the family.
Ask a parent to pair this device again.
Return to setup
```

### Native policy module

The module is now located at
`apps/mobile/modules/guardian-protection`. It contains the Expo bridge,
Kotlin policy verification, trusted-key handling, canonical JSON, policy
compilation/evaluation, snapshot rollback, encrypted policy storage,
monotonic counters, capability detection, and the current VPN baseline.

The shared Kotlin conformance runner is parameterized over every case in
`packages/test-fixtures/policy-decision-cases.json`. It compares action,
`reason_code`, `policy_rule_id`, and `bundle_stale`, and asserts that all
fixture cases execute. The current report is:

```text
tests="36" skipped="0" failures="0" errors="0"
```

The native signed-policy instrumented test previously passed against the real
backend:

```text
./gradlew :guardian-protection:connectedDebugAndroidTest --no-daemon
BUILD SUCCESSFUL
```

## Verification in this handoff

Node 22.12.0 was used for JavaScript checks:

```text
pnpm --filter guardian-mobile lint
passed

pnpm --filter guardian-mobile typecheck
passed
```

Native unit tests:

```text
./gradlew :guardian-protection:testDebugUnitTest --no-daemon
BUILD SUCCESSFUL in 12s
```

The focused conformance run also passed:

```text
./gradlew :guardian-protection:testDebugUnitTest --no-daemon \
  --tests expo.modules.guardianprotection.policy.SharedFixtureConformanceTest
BUILD SUCCESSFUL in 13s
```

Android builds:

```text
./gradlew :app:assembleDebug --no-daemon
BUILD SUCCESSFUL in 2m 42s

./gradlew :app:assembleRelease --no-daemon
BUILD SUCCESSFUL in 41s
```

Release manifest inspection found no cleartext attribute in the main source
manifest. Cleartext remains only in the debug and debugOptimized manifests:

```text
apps/mobile/android/app/src/debug/AndroidManifest.xml
apps/mobile/android/app/src/debugOptimized/AndroidManifest.xml
```

The API client uses `http://10.0.2.2:8000` only in development and rejects a
non-HTTPS configured URL in release. The documented configuration is in
`apps/mobile/.env.example`.

## Partially complete

### Slice 1.7 VPN enforcement

`GuardianVpnService` is a real foreground `VpnService` with TUN establishment,
semantic protection-status/failure reporting, and a DNS-specific IPv4 UDP
baseline. It can inspect DNS names, evaluate them against the active compiled
snapshot, return a blocked DNS response, and forward allowed DNS queries
through a protected upstream socket.

The requested full enforcement is not complete. The service currently routes
only the DNS endpoint rather than all traffic. IPv6, general TCP forwarding,
general UDP forwarding, QUIC/UDP-443 policy handling, complete flow
attribution, boot persistence, competing-VPN handling, captive-portal
classification, and emulator proof of blocked/allowed domain behavior through
the bridge remain open.

No anti-tamper claim is made beyond standard Android installation behavior.

### Device proof of possession

The device keypair is generated and stored, but request signing and
server-side proof-of-possession verification are not yet wired into
device-authenticated mutating requests or credential refresh.

### Generated API client

The mobile API client is typed, but it is not yet generated from the FastAPI
OpenAPI schema into a separate workspace package. A regeneration and CI drift
check remain open.

### Mobile test depth

The existing mobile tests cover only a small foundation surface. Auth/session
refresh and 401 recovery, SecureStore boundaries, pairing expiry/wrong-code/
lockout, role persistence and irreversible child-role protection, and the full
shared §31 state-component matrix still need dedicated tests.

## Remaining Phase 1 work

1. Finish Slice 1.7 real VPN forwarding and domain enforcement, including
   blocked/allowed emulator evidence and all §10.15 failure modes.
2. Implement device proof-of-possession request signing and server verification.
3. Generate the OpenAPI client and add the committed-output drift check.
4. Finish physical extraction of `route_handlers.py` implementations into
   owning modules.
5. Expand mobile unit/component tests.
6. Continue Slice 1.8 UsageStats, inventory, Accessibility, and notification
   enforcement.
7. Complete later Phase 1 sync, push, and platform work.

## Architecture state

- `apps/mobile` is an Expo SDK 57 application with committed native projects.
- `apps/mobile/modules/guardian-protection` is a local Expo module.
- JavaScript consumes shared contracts and policy-schema packages rather than
  redeclaring domain types.
- Android policy evaluation uses a compiled immutable snapshot and atomic
  active/previous snapshot storage.
- Policy signatures use Ed25519, `key_id`, canonical JSON bytes, and a trusted
  public-key set.
- Device and parent credentials are stored in SecureStore on mobile; native
  policy and counters use Android Keystore-backed encrypted storage.
- Backend and Postgres are local development services. The Android emulator
  reaches the backend through `10.0.2.2:8000` in debug builds.

## External blockers

- iOS verification requires macOS/Xcode and Apple entitlements.
- No GitHub remote exists yet.
- APNs/FCM credentials are absent.

## Known defects and limitations

- Full VPN packet forwarding and enforcement are not yet production complete.
- Device key proof-of-possession is not yet active.
- API generation/drift enforcement is absent.
- `backend/app/api/route_handlers.py` remains as an implementation
  concentration point even though route registration is modular.
- The emulator cannot prove iOS behavior on this Linux host.
- The current Android VPN path has not yet produced the requested real
  blocked-domain/allowed-domain bridge evidence.

## Exact next task

Implement the remaining Slice 1.7 VPN engine: full-route IPv4/IPv6 TCP and UDP
forwarding with DNS inspection, QUIC/UDP-443 policy behavior, flow
attribution, explicit VPN lifecycle/failure-mode handling, and an emulator
test that observes one blocked domain fail and one allowed domain succeed while
receiving only a semantic `WEB_BLOCKED` event through the bridge. Do not
advance to Slice 1.8 until that evidence exists.
