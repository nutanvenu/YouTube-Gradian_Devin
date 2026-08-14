# Devin Checkpoint

## Current phase

Phase 1 mobile surfaces are implemented and the emulator acceptance run is
complete for the parent-limit/request/approval loop. Slice 1.7 is accepted on the emulator with Option B selective routing
and dynamic blocked-destination routes. The old hand-rolled TCP proxy has been
removed from the service and the architecture decision is recorded in
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
corepack pnpm test -- --runInBand
Test Files 6 passed (6)
Tests 60 passed (60)

corepack pnpm --filter guardian-mobile lint
passed

corepack pnpm --filter guardian-mobile typecheck
passed
```

Backend signing tests, using the configured Python 3.13.1 interpreter:

```text
/home/ubuntu/.pyenv/versions/3.13.1/bin/python -m pytest -q tests/test_policy_signing.py
4 passed in 0.02s
```

The valid local backend remained reachable after startup validation:

```text
curl ... http://127.0.0.1:8000/v1/policy/public-key
policy_public_key_http=200
```

After the selective-routing packet-loop and event-dedup fixes:

```text
./gradlew :guardian-protection:testDebugUnitTest :app:assembleDebug --no-daemon
BUILD SUCCESSFUL in 20s
Performing Streamed Install
Success
```

Unsupported protocols such as ICMP are now ignored when they enter the
selective TUN. Repeated `WEB_BLOCKED` reports are deduplicated for 60 seconds
by domain so DNS and subsequent blocked packets produce one semantic event for
an attempt.

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

## Fresh selective-routing evidence

The standalone debug APK was installed on `guardian-api35` and the persisted
signed policy was active at version 5:

```text
DOMAIN_BLOCK blocked.example.com
DOMAIN_ALLOW example.com
Policy version: 5
```

Android reported the VPN's selective routes rather than a default route:

```text
VPN CONNECTED ... sessionId=Guardian protection
Routes: 10.0.2.3/32, 1.1.1.1/32, 1.0.0.1/32, 8.8.8.8/32,
8.8.4.4/32, 9.9.9.9/32, 10.0.0.2/32, fd00::2/128
```

Both navigation attempts were launched as Chrome, not from an adb shell. The
allowed-domain screenshot is:

```text
.scratch/emulator/option-b-allowed-after-fix.png
```

The clean blocked-domain attempt produced this screenshot and filtered bridge
evidence:

```text
.scratch/emulator/option-b-blocked-dedup.png
.scratch/emulator/option-b-blocked-dedup-events.txt
```

The event file contains exactly one semantic event:

```text
web_blocked_count=1
'GUARDIAN_BRIDGE_EVENT',
'{"type":"WEB_BLOCKED","domain":"blocked.example.com","category":null,"appRef":"com.android.chrome","reasonCode":"EXPLICIT_TARGET_RULE"}'
```

No packet-level bridge event was present in the filtered output. A subsequent
attempt before the deduplication fix emitted a second event without app
attribution after six seconds; that finding caused the 60-second fix.

The full acceptance gate is not complete on this run. The selected
`blocked.example.com` response did not provide an A/AAAA lease, so the live
route dump did not contain a dynamic route for that hostname. The direct-IP
blocked-destination requirement is therefore unproven; the known resolver
routes are not a substitute. Reboot, VPN-consent revocation/re-consent,
backend-down, and no-policy cases also require a fresh post-fix run rather
than relying on older evidence.

## Fresh post-DNS selective-routing evidence

The correctly trusted-key-configured debug APK applied real signed policy
version 7:

```text
DOMAIN_BLOCK example.org
DOMAIN_ALLOW example.com
GUARDIAN_BRIDGE_EVENT {"type":"POLICY_APPLIED","version":7}
```

Chrome was used for all network attempts. A blocked `example.org` navigation
failed and delivered exactly one semantic event with responsible-app
attribution:

```text
.scratch/emulator/option-b-v7-blocked-example-org.png
.scratch/emulator/option-b-v7-blocked-logcat.txt
WEB_BLOCKED {"domain":"example.org","category":null,
  "appRef":"com.android.chrome","reasonCode":"EXPLICIT_TARGET_RULE"}
```

The route dump after upstream A/AAAA learning contained both public IPv6
answers:

```text
.scratch/emulator/option-b-v7-routes-settled.txt
2606:4700:10::6814:1a88/128
2606:4700:10::ac42:9ded/128
```

Direct navigation to
`https://[2606:4700:10::6814:1a88]/` also failed through Chrome and produced
one attributed semantic event:

```text
.scratch/emulator/option-b-v7-direct-ipv6-final.png
.scratch/emulator/option-b-v7-direct-ipv6-final-logcat.txt
count=1
WEB_BLOCKED {"domain":"example.org","appRef":"com.android.chrome",
  "reasonCode":"EXPLICIT_TARGET_RULE"}
```

No packet-level bridge event appeared in the filtered logcat. The allowed
`https://example.com` navigation succeeded on the protected run:

```text
.scratch/emulator/option-b-v7-allowed-example-com.png
.scratch/emulator/option-b-v7-allowed-logcat.txt
```

The first route rebuild caused a transient Chrome `ERR_NETWORK_CHANGED`;
retrying after the rebuild settled produced the final evidence. With the
backend stopped, ordinary allowed traffic remained available:

```text
.scratch/emulator/option-b-v7-backend-down-allowed.png
```

With VPN unavailable and no active VPN route, ordinary traffic also remained
available (`vpn_route_present=0`):

```text
.scratch/emulator/option-b-v7-no-policy-allowed-final.png
```

VPN consent degradation was exercised with Android app-ops:

```text
ACTIVATE_VPN: ignore
ESTABLISH_VPN_SERVICE: ignore
capability:"vpn_filtering","state":"UNAVAILABLE"
```

Evidence:

```text
.scratch/emulator/option-b-v7-vpn-revoked.png
.scratch/emulator/option-b-v7-vpn-revoked-logcat.txt
.scratch/emulator/option-b-v7-vpn-reconsent-final.png
.scratch/emulator/option-b-v7-vpn-reconsent-final-logcat.txt
```

Restoring both app-ops returned `vpn_filtering` to `FULL` and re-established
the VPN. A transient Android TUN race observed in an earlier run is covered by
the service's four-attempt, 250 ms retry sequence; the settled reboot evidence
is recorded in the Slice 1.7 artifacts below.

## Slice 1.8 implementation status

Implemented in the local module and accepted on the emulator:

- `UsageStatsManager.queryEvents()` and `UsageEvents` transition mapping to
  foreground sessions, with pause/stop/foreground-switch handling.
- Local-midnight splitting using the selected `ZoneId`, daily app/category/device
  aggregation, encrypted daily snapshots, max-on-merge monotonicity, and
  summary date filtering.
- Usage collection queries a preceding event window so a foreground session
  already active at local midnight/range start is carried into the day rather
  than undercounted.
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

The usage-session suite includes a regression case for a foreground session
that began before the collection range and passed as part of that run.

TypeScript verification:

```text
corepack pnpm --filter guardian-mobile typecheck
tsc --noEmit
```

The earlier connected-test signing-key failure is resolved. The backend now
validates its key through the FastAPI lifespan, and the running local process
uses the generated ignored `backend/.env` key. The current backend endpoint
check returned HTTP 200 as recorded above.

## Fresh Slice 1.8 acceptance evidence

The live emulator run used child `83ff7aee-b11a-43ca-9432-b868a9d055c2`,
Chrome (`com.android.chrome`) as the real app under control, the local signed
backend policy, Usage Access, and the real bound Guardian AccessibilityService.
The backend process was running with the generated ignored signing key; policy
mutations produced versions 9 through 13.

An applied zero-minute Chrome limit (policy version 9) produced a real semantic
event:

```text
POLICY_APPLIED {"version":9}
APP_BLOCKED {"appRef":"com.android.chrome","reasonCode":"BUDGET_EXHAUSTED"}
```

Evidence:

```text
.scratch/emulator/slice18-policy9-restart-logcat.txt
.scratch/emulator/slice18-app-blocked-logcat.txt
.scratch/emulator/slice18-app-blocked-surface.png
```

The screenshot shows the child app's policy status and the surfaced
`APP_BLOCKED: com.android.chrome · BUDGET_EXHAUSTED` record. The first attempt
also exposed that the native block activity was immediately closed by the
asynchronous global Back action. The service now starts that activity after a
short main-thread delay. After rebuilding and reinstalling, the real native
surface remained resumed and displayed:

```text
This app is unavailable right now.
Your time limit or routine applies. Ask a parent to change the limit or routine if you need more time.
RETURN
```

Fresh visual/system evidence:

```text
.scratch/emulator/slice18-rebuilt-block-surface-3s.png
.scratch/emulator/slice18-rebuilt-block-logcat.txt
```

A scheduled routine was applied as policy version 12 with a window
`18:12-18:15` UTC on the emulator date and `com.android.chrome` in
`blocked_apps`. During the window, Chrome generated:

```text
APP_BLOCKED {"appRef":"com.android.chrome","reasonCode":"SCHEDULED_ROUTINE"}
```

and the block activity was launched. After the boundary at `18:15`, Chrome
remained the resumed activity and no `APP_BLOCKED` event was emitted:

```text
.scratch/emulator/slice18-policy12-apply-logcat.txt
.scratch/emulator/slice18-routine-active-logcat.txt
.scratch/emulator/slice18-routine-active-block.png
.scratch/emulator/slice18-routine-inactive-logcat.txt
.scratch/emulator/slice18-routine-inactive.png
```

Usage Access revocation and recovery were exercised through the emulator's
app-ops equivalent of the Android settings permission:

```text
adb -s emulator-5554 shell appops set com.guardian.family android:get_usage_stats ignore
```

The bridge reported `app_usage` `UNAVAILABLE` and degraded protection with
`details:"app_usage,notification_signals"`. Restoring access:

```text
adb -s emulator-5554 shell appops set com.guardian.family android:get_usage_stats allow
```

returned `app_usage` to `FULL` and removed it from the degraded details.
Evidence:

```text
.scratch/emulator/slice18-usage-revoked-logcat.txt
.scratch/emulator/slice18-usage-restored-logcat.txt
```

Policy version 13 restored a zero-minute Chrome limit before reboot. After
`adb reboot`, the boot receiver restarted the AccessibilityService and VPN
without opening the app. The system reported the persisted service and VPN:

```text
accessibility=com.guardian.family/expo.modules.guardianprotection.accessibility.GuardianAccessibilityService
sessionId=Guardian protection
```

Opening Chrome after boot launched `GuardianBlockActivity` for the persisted
limit, as shown by the activity-manager log. The boot-time service and VPN
were restored without opening the app. The JS process was not connected during
this boot-only probe, so this post-boot block has system/activity evidence but
not a fresh JS `APP_BLOCKED` line:

```text
.scratch/emulator/slice18-postboot-logcat.txt
.scratch/emulator/slice18-postboot-app-logcat.txt
.scratch/emulator/slice18-postboot-enforcement-logcat.txt
.scratch/emulator/slice18-postboot-block.png
.scratch/emulator/slice18-rebuilt-postboot-logcat.txt
.scratch/emulator/slice18-rebuilt-postboot-enforcement-logcat.txt
.scratch/emulator/slice18-rebuilt-postboot-block-surface.png
```

The reboot run therefore proves persisted policy/service/VPN recovery and
post-boot enforcement launch. The zero-minute rule does not expose a numeric
counter in the bridge, so a numeric live counter value is not independently
observable from the current UI; encrypted monotonic persistence remains
covered by JVM tests while the live reboot evidence is the persisted policy
plus enforcement result.

## Phase 1 parent-limit/request/approval acceptance

The remaining product loop was exercised against the real backend and
emulator. The child created a `MORE_TIME` request for
`com.android.chrome`; the parent inbox returned it as `PENDING`, and the
parent approved it with the reason `Approved for homework; one hour
exception.` The approval created signed policy version 15 from version 14.

Evidence from the child UI and backend:

```text
.scratch/emulator/phase1-loop-child-policy14-ack-logcat.txt
.scratch/emulator/phase1-loop-approved-logcat.txt
.scratch/emulator/phase1-loop-approved-regained.png
```

The child applied version 15, acknowledged it through
`POST /v1/devices/me/policy/ack`, and sent a capability heartbeat. Parent
health then returned:

```text
state=DEGRADED
policy_version_applied=15
last_seen_at=2026-08-14T18:35:23.585210Z
```

The child UI displayed `Policy acknowledged by this device.` and Chrome
remained the resumed activity after approval instead of launching the block
surface, demonstrating regained access. The health state is honestly
`DEGRADED` because Accessibility and notification capabilities are unavailable
on this emulator; acknowledgement does not imply full protection.

## VPN architecture decision

`docs/VPN_ARCHITECTURE_RESEARCH.md` records official Android documentation,
ecosystem evidence, and the accepted Option B decision. The TUN routes only
active DNS servers, known DoH/DoT resolver addresses, and a bounded TTL-aware
IPv4/IPv6 blocked-destination set. Ordinary allowed traffic bypasses Guardian;
this intentionally loses comprehensive non-DNS attribution, unrouted QUIC/DoH
enforcement, and complete IP-only enforcement.

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

`GuardianVpnService` is a real foreground `VpnService` with selective IPv4/IPv6
routes, DNS inspection/upstream forwarding, TTL-aware DNS-to-IP correlation,
bounded blocked-destination route updates, and semantic `WEB_BLOCKED`
reporting. Ordinary TCP/UDP traffic is not forwarded through userspace. TCP
and UDP packets that enter the TUN for a blocked destination are dropped and
evaluated against the local compiled snapshot; QUIC/UDP-443 is handled only
when its destination is in the routed set. IPv6 hop-by-hop, routing,
destination, and AH extension headers are parsed; fragmented IPv6 packets are
rejected because reassembly is not implemented.

Lifecycle handling is implemented for VPN consent revocation and competing VPN
revocation (`onRevoke`), process-kill restart (`START_STICKY`), persisted boot
restart (`BOOT_COMPLETED`), no network, unvalidated/captive-portal-like
networks, TUN setup failure, packet-loop failure, and upstream forwarding
failure. Failures are surfaced through protection health events and an
explicit stop path clears the persisted enabled state.

The fresh `example.org` run demonstrates selective route installation,
resolver blocking, direct-IP blocking, one semantic event with Chrome
attribution, allowed connectivity, backend-down/no-policy connectivity, and
VPN consent degradation/recovery. The TUN-establishment retry fix still needs
one rebuilt-APK reboot check before this slice is finally closed.

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

1. Add manual routine activation wiring to the native/local routine context.
2. Implement device proof-of-possession request signing and server verification.
3. Generate the OpenAPI client and add the committed-output drift check.
4. Finish physical extraction of `route_handlers.py` implementations into
   owning modules.
5. Expand mobile unit/component tests for the new surfaces and §31 states.
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
- Selective routing cannot enforce or attribute unrouted IP-only, QUIC, DoH,
  or competing-VPN traffic; this is a documented product limitation, not an
  anti-tamper claim.
- Android's `getConnectionOwnerUid` remains best-effort for TUN-originated
  tuples, but the clean blocked-domain run attributed the event to
  `com.android.chrome`.
- Device key proof-of-possession is not yet active.
- API generation/drift enforcement is absent.
- `backend/app/api/route_handlers.py` remains as an implementation
  concentration point even though route registration is modular.
- The emulator cannot prove iOS behavior on this Linux host.
- The authoritative fresh exact bridge-count evidence is
  `.scratch/emulator/option-b-v7-direct-ipv6-final-logcat.txt` (`count=1`);
  `.scratch/emulator/option-b-blocked-dedup-events.txt` is historical.
- The first post-fix reboot exposed a transient TUN race:
  `failed to add interface tun1 to VPN netId 102`. The rebuilt APK's boot run
  now restored the persisted VPN and AccessibilityService; a fresh settled
  route dump remains useful evidence.
- The first Slice 1.8 run exposed an Accessibility block-surface race: the
  service's Back action could close the activity it had just launched. The
  service now delays the launch after Back; the rebuilt APK screenshot and
  activity-manager evidence show the native surface is displayed.
- Manual routine activation is now carried in the signed policy as
  `base_policy.current_manual_routine_id`; the child applies that value to its
  persisted native snapshot and passes it into local app/domain evaluation.
- Schedule editing, unknown-app policy controls, and manual routine
  activation are exposed in the parent Rules screen and use real policy
  mutations. Rules show pending sync until the device acknowledges the
  resulting signed policy version.
- Backend startup now refuses missing/invalid signing configuration. The local
  ignored `backend/.env` contains a generated key for the current process.

## Fresh direct-IP re-confirmation

The upstream-resolve-then-route implementation was re-confirmed on the
currently installed debug APK with signed policy version 17. The parent
mutation sequence was:

```text
DOMAIN_BLOCK example.org -> policy_version=16
DOMAIN_ALLOW example.com -> policy_version=17
```

Chrome was used as the sandboxed network client. In one clean logcat capture:

- `https://example.org` failed at the resolver;
- the upstream response learned
  `2606:4700:10::6814:1a88` and installed
  `2606:4700:10::6814:1a88/128` in the VPN route set;
- direct navigation to
  `https://[2606:4700:10::6814:1a88]/` failed through the same Chrome
  process;
- `https://example.com` succeeded;
- exactly one semantic event crossed the JS bridge:

```text
WEB_BLOCKED {"domain":"example.org","category":null,
  "appRef":"com.android.chrome","reasonCode":"EXPLICIT_TARGET_RULE"}
web_blocked_count=1
```

The filtered capture contained no packet-level bridge event:

```text
.scratch/emulator/slice17-final2-blocked-resolver.png
.scratch/emulator/slice17-final2-direct-ip.png
.scratch/emulator/slice17-final2-allowed.png
.scratch/emulator/slice17-final2-routes-after-resolve.txt
.scratch/emulator/slice17-final2-semantic-events.txt
.scratch/emulator/slice17-final2-event-count.txt
```

The existing post-change lifecycle artifacts remain valid for this
implementation: VPN revocation reported `vpn_filtering=UNAVAILABLE`,
restored consent returned it to `FULL`, backend-down traffic remained
available, and ordinary traffic remained available with no active VPN/no
policy:

```text
.scratch/emulator/option-b-v7-vpn-revoked-logcat.txt
.scratch/emulator/option-b-v7-vpn-reconsent-final-logcat.txt
.scratch/emulator/option-b-v7-backend-down-allowed.png
.scratch/emulator/option-b-v7-no-policy-allowed-final.png
```

## Manual routine, schedule, and unknown-app implementation

The parent Rules screen now sends `ROUTINE_ACTIVATE` and
`ROUTINE_DEACTIVATE` mutations in addition to routine CRUD. The backend
creates a new signed policy version for each activation change, and the
native evaluator uses the signed `current_manual_routine_id` rather than a
JS-only flag. Schedule and unknown-app controls likewise send the real policy
mutation operations and remain pending until device acknowledgement.

Focused backend and native tests passed for activation/deactivation and local
manual-routine precedence. After rebuilding the debug APK with the trusted
backend key, a real backend mutation created policy version 18 and activated
`live-focus-2` as version 19:

```text
created_version=18
activated_version=19
active_manual_routine=live-focus-2
POLICY_APPLIED {"version":19}
APP_BLOCKED {"appRef":"com.android.chrome","reasonCode":"MANUAL_ROUTINE"}
topResumedActivity=...GuardianBlockActivity
```

Evidence:

```text
.scratch/emulator/item2-manual-routine-block-2.png
```

The first attempt correctly reported Accessibility as unavailable; the
service was then enabled through the real Android Accessibility settings
screen and the repeated Chrome launch displayed the native block activity.
This demonstrates the local manual-routine decision and block surface on the
emulator. The parent Rules screen and WebSocket invalidation source paths are
implemented, but a separate parent-role visual mutation/WebSocket capture
was not completed in this handoff.

## Remaining Phase 1 implementation handoff

This handoff added a durable child request outbox in SecureStore. Requests are
written locally while offline, carry a stable idempotency key, retry when the
network becomes reachable, and display a terminal `DEVICE_REVOKED` state when
the device is revoked before delivery. The child UI explicitly states that a
queued request unlocks nothing until approval reaches the device. Deterministic
queue/sync and revoked-device tests are in
`apps/mobile/src/state/request-outbox.test.ts`.

Device request proof-of-possession is now implemented for
`POST /v1/devices/me/requests`: the mobile client signs method, path, timestamp,
nonce, and SHA-256 body digest with the pairing key; the backend verifies the
stored Ed25519 public key, rejects stale/malformed proofs, and persists a
per-device nonce to prevent replay. Replay insertion now handles SQL
`IntegrityError` explicitly and rolls back the failed transaction. Pairing now
rejects invalid public keys.
Focused signature tests are in `backend/tests/test_device_auth.py`.

The generated API workspace is `packages/api-client`. Its deterministic output
comes from `scripts/generate_openapi_client.py`; `pnpm check:openapi` and
`.github/workflows/openapi.yml` enforce drift. Plain `/health` and `/livez`
report liveness; `/readiness` and `/readyz` run a database probe and signing-key
validation, returning 503 when either dependency is unavailable.

Mobile CI now has dedicated state and screen test jobs, with additional pairing,
request outbox, and 401-refresh coverage. The backend database was migrated to
the nonce table and the local runtime was restarted with the generated signing
key:

```text
GET /health       200 {"status":"ok"}
GET /readiness    200 {"status":"ready"}
```

Still open and not claimed: a dedicated live parent Rules mutation screenshot
for every control, a separate parent-edit-to-child WebSocket visual capture,
full extraction of `backend/app/api/route_handlers.py`, broader screen
component tests, and Mac-only iOS verification.

Nonce replay rows are pruned during proof validation using the same 300-second
freshness window as timestamp validation. This bounds `device_request_nonces`
while retaining replay protection for every still-fresh proof.

## iOS Slice 1.9 authoring

The iOS native layer is authored under `apps/mobile/ios`:

- `GuardianPolicyCore` is a small Swift Package containing canonical JSON,
  trusted-key Ed25519 verification through CryptoKit, policy evaluation,
  atomic active/previous bundle replacement, applied-version persistence, and
  fixture conformance tests against the exact
  `packages/test-fixtures/policy-decision-cases.json` file.
- `Guardian/GuardianProtectionModule.swift` provides the Expo bridge surface,
  Family Controls authorization/revocation capability reporting, shared
  App-Group status/usage storage, and honest `LIMITED` web-filtering reporting.
- Shield configuration/action, Device Activity monitor, and Network Extension
  data/control provider sources are under `GuardianExtensions`.
- `plugins/withGuardianIOS.ts` declares Family Controls, Network Extension,
  App Groups, usage descriptions, and extension targets. `PrivacyInfo.xcprivacy`
  declares the app's privacy access.

The implementation follows the current Apple contracts:

- Family Controls authorization:
  https://developer.apple.com/documentation/familycontrols/authorizationcenter/requestauthorization(for:)
- Managed Settings shields:
  https://developer.apple.com/documentation/managedsettingsui/shieldconfiguration
- Device Activity monitoring:
  https://developer.apple.com/documentation/deviceactivity
- Network Extension filtering:
  https://developer.apple.com/documentation/networkextension/nefilterdataprovider
- CryptoKit signing keys:
  https://developer.apple.com/documentation/cryptokit
- Expo iOS config-plugin mods:
  https://docs.expo.dev/versions/v57.0.0/config-plugins/mods/

Guardian's Android-level package inventory and arbitrary-domain attribution
are not available from Managed Settings or an NEFilter flow by default. The
iOS capability surface therefore reports `LIMITED`/`UNAVAILABLE` rather than
claiming unrestricted visibility. Managed Settings application tokens must
come from an authorized FamilyActivityPicker selection; raw package
identifiers in a signed policy cannot be silently treated as tokens.

The following remain explicitly unverifiable on this Linux host and require a
Mac with Xcode and the approved entitlement:

1. `xcodebuild` compilation of the app, Swift Package, and extension targets.
2. Family Controls entitlement request/approval in the Apple Developer portal.
3. iOS simulator execution and Device Activity/Shield/Network Extension runs.
4. Physical-device authorization, revocation, reboot, and enforcement testing.

The host has not claimed any of those results. A Mac verification entrypoint is
provided by `scripts/verify_ios_macos.sh` for the first available runner.

Final focused verification for this handoff:

```text
guardian-mobile lint       passed
guardian-mobile typecheck  passed
guardian-mobile Jest       4 suites, 9 tests passed
backend ruff               passed
backend focused pytest     3 passed, 6 deselected
GET /health                200 {"status":"ok"}
GET /readiness             200 {"status":"ready"}
git diff --check            passed
```

## Phase 1 closure work in progress

The active FastAPI application now includes each owning router exactly once;
family, health, and push duplicate registrations were removed. OpenAPI
generation completes without duplicate-operation warnings. The handler
implementations remain in `backend/app/api/route_handlers.py` and are
imported by the owning routers, so physical function relocation is still
outstanding even though the active route graph is unique.

Mobile transport now calls the generated `@guardian/api-client` workspace
client for request execution while retaining device proof headers and parent
token refresh behavior. The mobile surface tests were moved outside the Expo
Router route tree so Metro does not bundle test-only dependencies. The latest
mobile evidence is:

```text
Test Suites: 6 passed, 6 total
Tests:       23 passed, 23 total
guardian-mobile lint       passed
guardian-mobile typecheck  passed
```

The app reload after moving the tests reached the real child "My time" screen
on `emulator-5554`; the earlier Metro `Unable to resolve module console`
failure no longer reproduces. A dedicated parent-role Rules mutation run,
WebSocket no-refresh capture, and emulator offline queue/reconnect capture
remain required before those acceptance items can be claimed.

## Phase 1 verification gate

The Phase 1 code gate was run after the implementation commits on a clean
working tree. Root JavaScript checks passed under Node 22.12.0:

```text
pnpm lint       passed
pnpm typecheck  passed
pnpm test       6 files passed, 60 tests passed
```

Mobile checks passed:

```text
guardian-mobile lint       passed
guardian-mobile typecheck  passed
guardian-mobile Jest       6 suites passed, 23 tests passed
```

The complete backend suite passed:

```text
ruff check app tests       passed
mypy app                   Success: no issues found in 50 source files
pytest                    95 passed
```

An empty PostgreSQL database migrated from scratch to:

```text
0010_device_request_nonces
exit=0
```

Evidence log:
`.scratch/phase1-alembic-upgrade.log`.

The generated OpenAPI drift check passed with the active FastAPI route graph
and emitted no duplicate-operation warning:

```text
pnpm check:openapi          passed
```

Android verification passed:

```text
./gradlew :guardian-protection:testDebugUnitTest :app:assembleDebug :app:assembleRelease --no-daemon
BUILD SUCCESSFUL in 51s
./gradlew :app:connectedDebugAndroidTest --no-daemon
BUILD SUCCESSFUL in 34s
```

The live runtime remained available after the gate:

```text
GET /health       200 {"status":"ok"}
GET /readiness    200 {"status":"ready"}
metro             200
emulator-5554     device
PostgreSQL        healthy
```

The Phase 1 acceptance gate is not fully closed because live parent Rules
visual mutation, parent-to-child WebSocket invalidation, and emulator
offline-request reconnect evidence are still absent. Phase 2 must not begin
until those artifacts are captured.
