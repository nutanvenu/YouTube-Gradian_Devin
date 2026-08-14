# Devin Checkpoint

## Current phase

Phase 1, Slice 1.8 in progress: Android screen time, app inventory, and app controls.
Slice 1.7 has been accepted with emulator evidence; the hand-rolled full-route
TCP path remains a ship-blocking architecture decision documented separately in
`docs/VPN_ARCHITECTURE_RESEARCH.md`.

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
corepack pnpm --filter guardian-mobile test --runInBand
Test Suites: 2 passed, 2 total
Tests:       2 passed, 2 total

pnpm --filter guardian-mobile lint
passed

pnpm --filter guardian-mobile typecheck
passed
```

Native unit tests:

```text
./gradlew :guardian-protection:testDebugUnitTest --no-daemon
BUILD SUCCESSFUL in 26s
```

The focused packet-codec run passed after adding IPv6 extension-header and
fragment handling coverage:

```text
./gradlew :guardian-protection:testDebugUnitTest --no-daemon \
  --tests expo.modules.guardianprotection.vpn.PacketCodecTest
BUILD SUCCESSFUL
```

Android builds:

```text
./gradlew :app:assembleDebug --no-daemon
BUILD SUCCESSFUL in 2m 42s

./gradlew :app:assembleRelease --no-daemon
BUILD SUCCESSFUL in 49s
```

The module's emulator instrumented test also passed:

```text
./gradlew :guardian-protection:connectedDebugAndroidTest --no-daemon
Starting 1 tests on guardian-api35(AVD) - 15
Finished 1 tests on guardian-api35(AVD) - 15
BUILD SUCCESSFUL in 33s
```

The real package inventory/capability instrumented test passed after the
Slice 1.8 additions:

```text
adb -s emulator-5554 shell am instrument -w -r \
  -e class expo.modules.guardianprotection.GuardianProtectionInstrumentedTest#inventoryUsesRealPackageManagerDataAndCapabilityLevelsAreTruthful \
  expo.modules.guardianprotection.test/androidx.test.runner.AndroidJUnitRunner
OK (1 test)
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

The missing development-client splash-screen runtime dependency was fixed by
adding the Expo SDK 57 `expo-splash-screen` package. After rebuilding and
starting Metro, the development build loaded the real role-selection screen;
the dev-client menu was dismissed after the app bundle started. Evidence:

```text
.scratch/emulator/31-debug-role-selection-metro.png
.scratch/emulator/33-debug-role-selection-loaded.png
.scratch/emulator/34-role-selection.png
```

The development build logged:

```text
ReactNativeJS: Running "main" with {"rootTag":1,"initialProps":{},"fabric":true}
```

## Slice 1.8 implementation status

Implemented in the local module, but not yet accepted on the emulator:

- `UsageStatsManager.queryEvents()` and `UsageEvents` transition mapping to
  foreground sessions, with pause/stop/foreground-switch handling.
- Local-midnight splitting using the selected `ZoneId`, daily app/category/device
  aggregation, encrypted daily snapshots, max-on-merge monotonicity, and
  summary date filtering.
- Warning/expiry threshold tracking and runtime event hooks for app/category/
  device daily limits. Threshold state is reset when a new policy is installed.
- `PackageManager.getInstalledApplications()` inventory with launcher-query
  visibility declaration, labels, category mapping, Android resource icon URIs,
  persisted new-package detection, and parent-home rendering.
- Declared `AccessibilityService` with foreground window events, local policy
  evaluation, explicit/routine/limit blocking, calm native block activity, app
  attribution in `APP_BLOCKED`, and no high-frequency event bridge.
- Usage Access and Accessibility parent-facing explanation/recovery actions,
  real revocation checks, and degraded capability health.

Focused JVM verification after these edits:

```text
./gradlew :guardian-protection:testDebugUnitTest --no-daemon
BUILD SUCCESSFUL in 26s
```

TypeScript verification:

```text
corepack pnpm --filter guardian-mobile typecheck
tsc --noEmit
```

The full connected native test was attempted but is currently blocked by the
running backend configuration. It reached the real emulator and failed during
test fixture setup because the backend's signing key is absent:

```text
./gradlew :guardian-protection:connectedDebugAndroidTest --no-daemon
POST /v1/families/.../children -> 500
RuntimeError: GUARDIAN_POLICY_PRIVATE_KEY is not configured
```

This is an environment/configuration blocker, not a silently skipped test.
The inventory/capability test, which does not require the backend, passed on
the emulator as shown above.

## VPN architecture research

`docs/VPN_ARCHITECTURE_RESEARCH.md` records official Android documentation and
ecosystem evidence. No VPN architecture was changed. The decision is between
full-route TUN with a pinned mature userspace stack and selective DNS/blocked
range routing; Android `VpnManager` is a lifecycle/profile primitive, not a
general replacement for local inspection.

## Verification in the Slice 1.7 acceptance run

The acceptance run used the real `guardian-api35` emulator, Chrome as the
requesting application, the local FastAPI backend, PostgreSQL, and the signed
policy for version 5:

```text
DOMAIN_BLOCK blocked.example.com
DOMAIN_ALLOW example.com
```

The app rendered `Policy version: 5`, `Waiting for device acknowledgement.`,
and `Web protection is active.` The allowed-domain TCP proxy was fixed to
establish the protected upstream socket before sending the synthetic
SYN-ACK. After that fix, Chrome loaded `https://example.com` and displayed
`Connection is secure` / `Example Domain`:

```text
.scratch/emulator/58-allowed-after-tcp-fix.png
.scratch/emulator/76-no-policy-allowed.png
```

Chrome failed to resolve the blocked domain with
`DNS_PROBE_FINISHED_NXDOMAIN`:

```text
.scratch/emulator/59-blocked-after-tcp-fix.png
.scratch/emulator/55-bridge-events.txt
.scratch/emulator/60-bridge-event-after-reload.png
```

The filtered bridge evidence contains exactly one semantic event for the
fresh DNS attempt:

```text
'GUARDIAN_BRIDGE_EVENT',
'{"type":"WEB_BLOCKED","domain":"blocked.example.com","category":null,"appRef":"com.android.chrome","reasonCode":"EXPLICIT_TARGET_RULE"}'
```

No packet-level event string was present in the filtered bridge output. The
first navigation was served from Chrome's negative DNS cache and emitted no
new event; pressing Chrome Reload forced a fresh DNS request. That cache
behavior is why the exact-count evidence is from the reload attempt.

After `adb reboot`, the boot receiver started the foreground VPN service and
the emulator reported `Active vpn type: 1`, session `Guardian protection`.
The persisted policy remained available and the blocked-domain navigation
again settled on `DNS_PROBE_FINISHED_NXDOMAIN`:

```text
.scratch/emulator/61-reboot-recovery-logcat.txt
.scratch/emulator/63-reboot-blocked-settled.png
```

The VPN settings screen was used to disconnect the active VPN. With VPN
consent denied through Android app-ops for the emulator's system-state
exercise, the child screen reported `Web protection permission is required.`
and offered `Enable web protection`:

```text
.scratch/emulator/70-vpn-consent-revoked-degraded.png
.scratch/emulator/69-vpn-consent-revoked-logcat.txt
```

Restoring the VPN permission and returning to the app re-established the VPN,
and the screen returned to `Web protection is active.`:

```text
.scratch/emulator/74-vpn-reconsent-restored.png
```

With the backend process stopped, Chrome still loaded `example.com` while the
persisted local policy/VPN was active:

```text
.scratch/emulator/75-backend-down-allowed.png
```

With the protection service stopped (no active VPN), Chrome loaded
`Example Domain`, demonstrating ordinary connectivity is not bricked when
protection is unavailable:

```text
.scratch/emulator/76-no-policy-allowed.png
```

The backend was restarted on `0.0.0.0:8000`, PostgreSQL remained healthy, and
the emulator, Metro, and VPN were left running at handoff.

### Slice 1.7 VPN enforcement

`GuardianVpnService` is a real foreground `VpnService` with full IPv4/IPv6
default routes, TUN packet parsing, protected UDP forwarding, a userspace TCP
proxy, DNS inspection/upstream forwarding, DNS-to-IP correlation with TTL
expiry, and semantic `WEB_BLOCKED` reporting. IPv6 hop-by-hop, routing,
destination, and AH extension headers are parsed; fragmented IPv6 packets are
explicitly rejected because this service does not reassemble fragments.
Unknown-domain UDP/443 is dropped with `QUIC_DOMAIN_UNRESOLVED` only while an
active policy snapshot exists; if policy is unavailable, it is allowed so the
service cannot silently brick connectivity.

Lifecycle handling is implemented for VPN consent revocation and competing VPN
revocation (`onRevoke`), process-kill restart (`START_STICKY`), persisted boot
restart (`BOOT_COMPLETED`), no network, unvalidated/captive-portal-like
networks, TUN setup failure, packet-loop failure, and upstream forwarding
failure. Failures are surfaced through protection health events and an
explicit stop path clears the persisted enabled state.

The live acceptance run above demonstrates blocked/allowed app traffic,
semantic bridge delivery, Chrome attribution, reboot recovery, and
connectivity with the backend unavailable. The exact bridge count is
established by the filtered logcat file; the visible child-screen count is
not used as the count assertion because the screen had prior events in its
session.

The VPN-revocation exercise used the Android VPN settings disconnect action
plus an emulator-only `appops` denial to make `VpnService.prepare()` report
consent unavailable. This is strong system-state evidence, but it is not a
repeatable user-level "Forget consent" control exposed by Android settings.
The app degraded to the explicit permission-required state and recovered
after the permission was restored. Captive-portal and competing-VPN behavior
remain code-path/test evidence rather than a separately captured live
emulator scenario.

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

1. Implement device proof-of-possession request signing and server verification.
2. Generate the OpenAPI client and add the committed-output drift check.
3. Finish physical extraction of `route_handlers.py` implementations into
   owning modules.
4. Expand mobile unit/component tests.
5. Finish Slice 1.8 emulator acceptance: real app-limit exhaustion/block
   surface, routine boundary, Usage Access revocation degradation, reboot
   persistence, screenshots/logcat/semantic events. Restore the backend
   signing key before backend-dependent setup.
6. Complete later Phase 1 sync, push, and platform work.

## Architecture state

- `apps/mobile` is an Expo SDK 57 application with committed native projects.
- `apps/mobile/modules/guardian-protection` is a local Expo module.
- Android package structure includes `usage/`, `inventory/`, and
  `accessibility/`; UsageStats state is encrypted with the existing Keystore
  store and policy decisions run from the compiled local snapshot.
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

- Captive-portal and competing-VPN behavior remain code-path/test evidence
  rather than separately captured live emulator scenarios.
- TCP proxy retransmission, congestion/window management, and out-of-order
  packet handling are not production-grade yet.
- Android's `getConnectionOwnerUid` cannot be proven to recover the original
  app for a TUN-originated tuple on this emulator; attribution remains
  best-effort and is not live-verified.
- Device key proof-of-possession is not yet active.
- API generation/drift enforcement is absent.
- `backend/app/api/route_handlers.py` remains as an implementation
  concentration point even though route registration is modular.
- The emulator cannot prove iOS behavior on this Linux host.
- The exact bridge-count evidence is from the clean prior run in
  `.scratch/emulator/55-bridge-events.txt`; later Chrome runs were affected by
  Chrome startup/negative-DNS cache and are not used as the count assertion.
- Slice 1.8 has no valid end-to-end acceptance evidence yet. A real emulator
  run cannot create a new signed child policy while
  `GUARDIAN_POLICY_PRIVATE_KEY` is absent from the backend process environment.
- The current live backend returned HTTP 500 for child creation; the captured
  traceback is `RuntimeError: GUARDIAN_POLICY_PRIVATE_KEY is not configured`.

## Exact next task

Provide the backend's configured policy signing key to the running local
development process, then run Slice 1.8 emulator acceptance: pair a child,
apply a signed one-minute app limit and a routine, observe the real
Accessibility block surface and semantic events, cross the routine boundary,
revoke Usage Access and verify degraded health, reboot and verify persisted
counters/enforcement, and capture evidence. Do not claim Slice 1.8 accepted
until those scenarios pass.
