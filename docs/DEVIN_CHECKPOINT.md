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

The backend route registration and handler bodies are split into the owning
domain routers. Shared dependencies and lifecycle support live under
`backend/app/api/handler_support.py` and `backend/app/api/lifecycle.py`;
`backend/app/api/route_handlers.py` has been deleted.

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

## Historical Phase 1 work list

1. Add manual routine activation wiring to the native/local routine context.
2. Implement device proof-of-possession request signing and server verification.
3. Generate the OpenAPI client and add the committed-output drift check.
4. Finish physical extraction of `route_handlers.py` implementations into
   owning modules. (Completed in the current handoff.)
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
- Device key proof-of-possession is active for device-authenticated mutations.
- API generation/drift enforcement is present in the workspace check.
- Handler implementations are physically located in their owning routers;
  `backend/app/api/route_handlers.py` is deleted.
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

Still open and not claimed: broader screen component tests and Mac-only iOS
verification. The dedicated two-emulator parent-edit-to-child WebSocket
capture is recorded below.

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
generation completes without duplicate-operation warnings. Handler bodies
are physically located in their owning routers, with shared support isolated
under `app/api/handler_support.py`; the former god-file is deleted.

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

The Phase 1 acceptance gate's dedicated parent-to-child WebSocket no-refresh
visual capture is recorded below. Remaining Phase 1 follow-up is broader
screen/component coverage and Mac-only iOS verification.

## Phase 1 live evidence update

The live emulator run on `emulator-5554` completed the remaining visible
Rules mutations against the real parent session and paired child
`f6a73077-2876-40c6-b8bc-0b0a7b19142f`:

```text
policy version 4  DOMAIN_BLOCK example.org
policy version 5  APP_BLOCK (parent Rules UI)
policy version 6  UNKNOWN_APP_POLICY=BLOCK
```

The domain mutation's pending banner and child acknowledgement are captured
at:

```text
.scratch/emulator/phase1-rules-domain-pending-top.png
.scratch/emulator/phase1-child-domain-ack.png
```

The unknown-app mutation was driven through the actual Rules button and
confirmed in PostgreSQL as version 6 with `unknown_app_policy=BLOCK`.
The active post-reload Rules surface is:

```text
.scratch/emulator/phase1-rules-unknown-app-ack.png
```

The earlier app-limit and schedule artifacts remain:

```text
.scratch/emulator/phase1-rules-app-limit-pending.png
.scratch/emulator/phase1-rules-app-limit-ack.png
.scratch/emulator/phase1-rules-schedule-pending.png
.scratch/emulator/phase1-child-schedule-ack.png
```

Offline request queueing and reconnect delivery were exercised on the same
emulator. With Wi-Fi and mobile data disabled, the child request screen
showed the explicit caveat and durable queued state:

```text
.scratch/emulator/phase1-child-request-offline-queued.png
```

After connectivity was restored, the outbox flushed, the child showed
`Request delivered`, PostgreSQL recorded a real `MORE_TIME` request in
`PENDING`, and the parent inbox displayed `MORE_TIME / Waiting for a parent`:

```text
.scratch/emulator/phase1-child-request-reconnected.png
.scratch/emulator/phase1-parent-inbox-after-reconnect.png
```

The child policy now subscribes to the family WebSocket invalidation stream
and invalidates `device-policy` when a family event arrives. This code is
linted and typed, but a two-surface no-refresh visual capture is still
outstanding because this single-emulator run cannot keep the parent and child
surfaces simultaneously visible.

## Two-emulator WebSocket evidence and route extraction

The dedicated two-device harness now runs:

```text
parent: guardian-api35 / emulator-5554
child:  guardian-api35-child / emulator-5556
image:  system-images;android-35;google_apis;x86_64
```

The child was freshly paired through the real UI after the pairing response
began returning and persisting `family_id`. The child WebSocket hook was also
corrected to use the paired device token when no parent access token exists.
The backend log records the accepted device-authenticated subscription:

```text
WebSocket /v1/ws/sync?family_id=5abf06a7-3f24-4170-ab6b-2b41039dc331 [accepted]
```

No child interaction occurred between the initial and final captures:

```text
initial child: policy version 4
parent Rules mutation: APP_BLOCK, real policy version 5
final child: policy version 5
```

Artifacts:

```text
.scratch/emulator/ws/child-initial-version-4.png
.scratch/emulator/ws/parent-after-mutation.png
.scratch/emulator/ws/parent-final-version-5-pending.png
.scratch/emulator/ws/child-final-version-5.png
.scratch/emulator/ws/backend-websocket-evidence.log
```

The parent Rules screen displayed `Pending sync · device has not
acknowledged version 5` while the child surface changed from version 4 to
version 5 without refresh, reload, route reopen, or child interaction. The
child honestly remained in a pending/degraded protection state because the
emulator's web-protection capability was not enabled.

Physical route extraction is now complete. Handler bodies were moved into
their owning `auth`, `children`, `devices`, `events`, `families`, `pairing`,
`policies`, `push`, and `requests` routers. Shared authentication, policy,
rate-limit, and notifier dependencies live in
`backend/app/api/handler_support.py`; lifecycle validation lives in
`backend/app/api/lifecycle.py`. `backend/app/api/route_handlers.py` was
deleted rather than retained as a wrapper. OpenAPI generation completes
without duplicate-operation warnings.

Post-extraction verification:

```text
ruff check app tests       All checks passed
mypy app                   Success: no issues found in 51 source files
pytest                    95 passed
GET /readiness            200 {"status":"ready"}
```

## Phase 2 requests inbox and push actions

The first Phase 2 vertical slice adds interface-driven push notification
actions for child requests. Child request creation now generates independent
opaque approve and deny tokens for each active parent push registration,
persists only SHA-256 token hashes with an expiration, and invokes the
`PushSender` interface with a real action payload. `LoggingPushSender` remains
the development implementation because APNs/FCM credentials are external
configuration, not a reason to fake delivery.

The action endpoints are:

```text
POST /v1/push/actions/{action_token}/approve
POST /v1/push/actions/{action_token}/deny
```

They check the hashed token, action type, expiration, current family
guardianship, and request state. Repeating the same terminal action is
idempotent; an opposite action, invalid token, expired token, or revoked
parent is rejected. Valid actions reuse the authenticated parent
`decide_request` path, preserving policy mutation and WebSocket behavior.

The generated OpenAPI client now includes both endpoints and the corrected
`PushTokenIn.token` contract. Mobile push-action state handling routes a
validated notification payload to the action endpoint without embedding
approval logic in the UI.

Focused and full backend verification for this slice:

```text
ruff check app tests                 All checks passed
mypy app                             Success: no issues found in 51 source files
pytest                               98 passed in 6.82s
pytest tests/test_push_actions.py    3 passed
```

Mobile verification:

```text
lint                                passed
typecheck                           passed
Jest                                7 suites, 25 tests passed
```

The live development database is at Alembic revision `0011_push_actions`.
The backend was restarted after applying the migration; APNs/FCM delivery
itself remains intentionally unclaimed until provider credentials are
available.

## Fresh two-emulator WebSocket and push-action evidence

The two-device run was repeated with the parent app on `emulator-5554` and
the paired child app on `emulator-5556`. The parent Rules screen performed a
real `APP_BLOCK` mutation while the child remained on its home surface:

```text
child before: Policy version: 6
parent mutation: policy version 7, Pending sync
child after: Policy version: 7
```

The child changed without refresh, route reopen, reload, or child
interaction. The visual artifacts and UI hierarchy are:

```text
.scratch/emulator/ws-current/child-before-version6.png
.scratch/emulator/ws-current/parent-after-mutation-version7-pending.png
.scratch/emulator/ws-current/child-after-websocket-version7.png
.scratch/emulator/ws-current/child-after-websocket-version7.xml
.scratch/emulator/ws-current/backend-websocket-evidence.log
```

The backend evidence contains the successful parent mutation, accepted
WebSocket subscription, and the child's subsequent policy fetch. The
emulator still reports a pending/degraded protection state because its web
protection capability is unavailable; this does not affect policy-version
propagation.

Provider delivery was not claimed. For the action path that does not require
APNs/FCM, a real pending child request was paired with a backend-generated
approve/deny payload and delivered to the running app's
`handleRequestPushAction` handler on `emulator-5554`. The handler called the
opaque approve path and the backend returned 200:

```text
request: 673affb0-6561-4ed5-8f1f-569bc3872b2b
terminal state: APPROVED
decision reason: Approved from notification
```

Artifacts:

```text
.scratch/emulator/push/synthetic-payload-redacted.json
.scratch/emulator/push/synthetic-handler.png
.scratch/emulator/push/synthetic-handler.xml
.scratch/emulator/push/backend-synthetic-action.log
```

APNs/FCM provider delivery and notification-tap plumbing remain unverified
pending provider credentials. The family-scoped health route used by the
parent UI was also added at `GET /v1/families/{family_id}/health`; an
authenticated live request returned the device health records, and the
generated client contract was regenerated accordingly.

## Route inventory and reproducible backend dependencies

The missing family health route exposed a failure mode in which route
registrations could disappear during extraction without a compile-time error.
`backend/tests/test_route_inventory.py` now defines the complete expected
application inventory as `(path, method, auth kind)` entries, including the
WebSocket route. It derives the registered table from the FastAPI app,
rejects duplicate entries, and compares the result to the explicit inventory.
The current audit found no other missing HTTP routes:

```text
registered HTTP routes: 41
OpenAPI HTTP routes:     41
missing from OpenAPI:    []
extra in OpenAPI:        []
WebSocket routes:        /v1/ws/sync
```

Backend dependency installation now has one story: `uv`, pinned by
`.uv-version`, with exact project requirements in `backend/pyproject.toml`
and resolved artifacts in `backend/uv.lock`. CI uses
`uv sync --locked --extra dev` and executes migrations, lint, type checking,
and tests through `uv run`. The OpenAPI drift job uses the same locked
environment.

The explicit route inventory was extended while starting the Activity slice.
The audit found two additional client-visible registrations that had never
been present in the backend table:

```text
GET /v1/families
GET /v1/families/{family_id}/activity
GET /v1/families/{family_id}/activity/usage
```

The first is used during mobile session family discovery; the latter two
back the parent Activity screen. They are now registered in the owning
families and events routers and covered by the inventory guard. The current
registered table is:

```text
registered HTTP routes: 47
WebSocket routes:       /v1/ws/sync
```

`backend/app/api/route_handlers.py` remains deleted; handler bodies are
owned by their feature routers. The route inventory test now fails if any of
these paths is dropped, duplicated, or changes authentication category.

## Phase 2 rich Activity dashboard (backend and contract slice)

The Activity backend now exposes real persisted data:

```text
GET /v1/families/{family_id}/activity
GET /v1/families/{family_id}/activity/usage
```

The first returns persisted web and safety events, including domain, app,
category, and occurrence time. The second returns persisted usage points
with app, category, duration, event type, and occurrence time. Device event
ingestion now accepts category and bounded duration fields, routes
`WEB_*` events to web history, and stores categories for web and safety
events. Migration `0012_event_categories` adds the persisted columns.
Unknown values remain `null` and render as `Unknown` in the mobile Activity
screen; no usage numbers are fabricated.

The mobile Activity screen now queries both backend endpoints, renders web
history and usage-over-time points, and preserves loading, error, offline,
stale, and unknown/empty states. Generated OpenAPI output includes the
typed Activity response schemas and all three newly audited paths.

Automated evidence:

```text
pytest tests/test_route_inventory.py tests/test_activity.py   2 passed
ruff check app tests/test_activity.py tests/test_route_inventory.py  passed
mypy app                                                   success, 51 files
guardian-mobile typecheck                                  passed
guardian-mobile lint                                       passed
guardian-mobile Jest                                       7 suites, 25 tests passed
alembic current                                            0013_child_app_inventory
```

The test posts a real device-authenticated `WEB_BLOCKED` event and an
`APP_USAGE` point, then reads them through the authenticated family Activity
endpoints.

Live two-emulator evidence is now captured for family
`d654598b-6ef2-4eca-b001-e0017d2180ac` and child
`ee25390f-e0ec-4865-86e1-0a9437a1bf13`:

```text
.scratch/emulator/activity-parent-live-web-event.png
.scratch/emulator/activity-parent-live-web-event.xml
.scratch/emulator/activity-parent-live-data.png
.scratch/emulator/activity-child-blocked-live2.png
.scratch/emulator/activity-child-blocked-live-logcat2.txt
.scratch/emulator/activity-parent-offline-state.png
.scratch/emulator/activity-parent-offline-state.xml
```

The child policy mutation added an explicit `blocked.example.com` block,
the child VPN was restarted after consent recovery, and Chrome produced a
real native event:

```text
WEB_BLOCKED | blocked.example.com | category=null | app_ref=com.android.chrome
POST /v1/devices/me/events 202 Accepted
web_events rows: 1
usage_aggregates rows: 27
```

The parent Activity visibly rendered `WEB_BLOCKED`,
`blocked.example.com`, and `Unknown category`, alongside backend-derived
usage points. A separate airplane-mode run visibly rendered
`You're offline. Last-known data may be shown.` as the §31 offline state.

## Phase 2 app-controls review slice

Android package inventory now persists both the known package set and a
pending-review set in the device's Guardian inventory preferences. Newly
observed packages remain pending across repeated inventory reads until the
parent explicitly marks the package reviewed. The parent Rules screen shows
an explicit review warning and action before presenting the app as trusted;
Allow, Block, Limit, Schedule, and Unlimited remain separate signed-policy
mutations. The native bridge and shared contract expose the review action.

The no-family parent home state also keeps the `Set up your family` action
visible outside the empty `DataState`, preventing a dead end when no active
family has been selected.

Automated evidence:

```text
guardian-mobile typecheck                                  passed
guardian-mobile lint                                       passed
guardian-mobile Jest                                       7 suites, 26 tests passed
guardian-protection AppInventoryTest                       BUILD SUCCESSFUL
uv lock --check                                             Resolved 54 packages
```

The child inventory synchronization slice now persists minimized observed app
records in the backend per child profile (`0013_child_app_inventory`).
`POST /v1/devices/me/inventory` is device-authenticated and upserts bounded
package identifiers, display names, categories, and observation times.
Parent-authenticated Rules reads use
`GET /v1/families/{family_id}/children/{child_id}/inventory`, and review
decisions use the corresponding parent-authenticated review mutation. Review
timestamps and the reviewing parent are stored server-side, so repeated
uploads preserve review state and multiple devices converge on the same
child-level records. The mobile child uploads its minimized inventory after
protection sync; the parent Rules screen no longer reads device-local
inventory.

The child Activity surface now forwards native `WEB_BLOCKED` events and
non-zero native usage summaries through the minimized
`POST /v1/devices/me/events` contract. This path was typechecked, linted, and
covered by the existing mobile test suite. Repeated inventory uploads are
implemented as PostgreSQL upserts that preserve `reviewed_at` and
`reviewed_by_parent_id`, including duplicate package identifiers in one
upload. This avoids the previously observed unique-constraint failures during
repeated device inventory reporting.

Live backend inventory authorization and persistence evidence:

```text
pytest tests/test_inventory.py tests/test_route_inventory.py   3 passed
```

The focused inventory regression suite now includes duplicate-upload and
review-preservation coverage:

```text
pytest backend/tests/test_inventory.py   3 passed
```

## Phase 2 reputation slice

The backend now stores source-attributed domain verdicts and publishes signed,
versioned full bundles and chained deltas using the policy Ed25519
`key_id`/canonical-byte machinery. The default provider is intentionally
conservative: the shipped `example.com` entry is a source-attributed
placeholder seed (`KNOWN_SAFE` for the reserved documentation domain), and all
other identifiers resolve to explicit `UNKNOWN` with no fabricated score or
confidence. The seed list is not presented as useful reputation coverage. A
real third-party reputation feed remains an external provider integration
point pending integration and is not claimed here.

Classification accepts only a normalized domain identifier. Full URLs, paths,
queries, and browsing-history fields are rejected at the API boundary. Device
sync returns a full bundle when a delta chain is unavailable; Android retains
the last-known-good snapshot when schema, signature, version, or delta-chain
validation fails.

Android local evaluation now supports `KNOWN_SAFE`, `KNOWN_RISK`, and
`UNKNOWN`, with bounded 30-second pending state. Explicit parent rules remain
ahead of reputation. Younger policies block while classifying and on expiry;
older policies allow-and-notify while classifying and on expiry. The parent
Rules screen shows bundle version, source-attributed verdicts, explicit
`UNKNOWN`, and `Still classifying` instead of a fabricated confidence.

Focused evidence:

```text
backend pytest                                      105 passed
backend ruff                                        passed
OpenAPI generation                                  passed
root typecheck                                      passed
guardian-mobile typecheck                           passed
guardian-protection reputation JVM tests            BUILD SUCCESSFUL
guardian-protection large bundle                   10,000 entries; encoded size and apply time reported
alembic head                                        0014_reputation
```

The native large-bundle test reports encoded size, apply duration, and an
explicit bounded-memory estimate of 512 bytes per retained entry
(5,120,000 bytes for 10,000 entries). This is an upper-bound accounting
estimate, not a platform heap profile; a device heap profiler remains useful
for release benchmarking and is not represented as measured here.

The Android debug APK was rebuilt with the backend's trusted
`guardian-dev` public key and installed on both live emulators. The child then
applied the signed full bundle and emitted:

```text
GET /v1/devices/me/reputation?version=0 HTTP/1.1 200 OK
REPUTATION_STATUS_CHANGED {"version":1,"reason":"APPLIED"}
VPN CONNECTED InterfaceName: tun0
```

The development database at that point contained reputation version 1, one
source-attributed curated entry (`example.com`, `KNOWN_SAFE`), and one `FULL`
revision. The previous `SIGNATURE_INVALID` result was therefore an
APK-configuration failure, not a backend signature or route failure. The
signed-build artifact is
`.scratch/emulator/reputation/child-main-after-signed.png`.

The live unknown-domain flow was subsequently captured on child
`emulator-5556` with a live Metro JavaScript session and current policy version
5. The temporary signed fixture put the child in `YOUNG_CHILD`,
`BLOCK_WHILE_CLASSIFYING`, with no scheduled routines. The evidence chain is:

```text
ReactNativeJS: Running "main"
POLICY_APPLIED {"version":5}
VPN CONNECTED InterfaceName: tun0
WEB_BLOCKED domain=optimizationguide-pa.googleapis.com
  reasonCode=REPUTATION_PENDING
POST /v1/devices/me/reputation/classify 200 OK
GET /v1/devices/me/reputation?version=1 200 OK
REPUTATION_STATUS_CHANGED {"version":7,"reason":"APPLIED"}
WEB_BLOCKED domain=optimizationguide-pa.googleapis.com
  reasonCode=UNKNOWN_DOMAIN_POLICY
```

The backend persisted `unknown-reputation.example` as an explicit `UNKNOWN`
from `guardian-curated-seed` with the deterministic rationale that no curated
verdict was available. Its signed revision was a `DELTA` with
`base_version=1`, and the request boundary accepted only the normalized domain
identifier; no URL, path, query, fragment, or browsing history was stored.
Chrome also generated background DNS requests, which produced additional
minimized identifiers and chained deltas (versions 3 through 7); those are
visible in `.scratch/emulator/reputation/live-result-db.txt`.

The second native event demonstrates the post-verdict younger-band behavior:
once the signed `UNKNOWN` entry was locally available, the request no longer
used the pending reason and remained blocked by the configured unknown-domain
policy. The temporary fixture was then restored through a signed policy update:
the child applied policy version 6 with its original `TEEN`,
`ALLOW_AND_NOTIFY`, and scheduled-routine settings.

Live evidence artifacts:

```text
.scratch/emulator/reputation/live-attempt.log
.scratch/emulator/reputation/live-result-db.txt
.scratch/emulator/reputation/live-evidence-summary.txt
.scratch/emulator/reputation/live-child-events.txt
.scratch/emulator/reputation/live-logcat-final.txt
```

The native large-bundle check covers 10,000 entries. It reports the encoded
bundle size and apply duration through the native apply result, plus the
bounded-memory estimate of 512 bytes per retained entry:

```text
entryCount=10000
encodedBytes=1919047
applyMillis=195
estimatedMemoryBytes=5120000
```

The memory value is an upper-bound accounting estimate, not a platform heap
profile. The live delta application emitted `version=7/APPLIED`; its bridge
event does not expose the apply metrics, so the JVM performance artifact
(`TEST-expo.modules.guardianprotection.reputation.ReputationManagerTest.xml`)
is the source for the numeric bundle measurements.

The child-side sync/classification transport now requests only the event's
minimized domain, applies full/delta responses locally, and refetches a full
bundle after `DELTA_GAP`. The live pending/resolve run is now recorded for the
younger-band path; APNs/FCM delivery remains outside this slice and requires
provider credentials.

Phase 2 usage reports and safety notification routing are now implemented.
`GET /v1/families/{family_id}/usage/reports` derives daily or weekly buckets
from persisted `usage_aggregates`, joins all devices for the selected child,
splits durations at local calendar boundaries using an IANA timezone, and
preserves each event's source timezone. The report contract includes explicit
period, total duration, event count, per-app, and per-category totals. The
mobile Activity surface renders the report through the existing loading,
empty, offline, stale, permission-denied, and error state machinery; absent
persisted data remains `Unknown` rather than a fabricated zero.

Focused report tests cover a DST transition, a timezone change in the report
view, weekly aggregation across two devices for one child, and route
authorization. The earlier empty report was ownership-correct: the queried
family `8bffc14d-747e-4e56-aa3f-104839a2fe25` had no aggregates, while the 69
rows belonged to families `d654598b-6ef2-4eca-b001-e0017d2180ac` (63 rows)
and `5abf06a7-3f24-4170-ab6b-2b41039dc331` (6 rows). The live backend is now
migrated to `0018_safety_routing_outcomes`. A fresh authenticated
data-owning-family run returned one populated daily report bucket, two usage
rows, and one activity event. Runtime evidence is in
`.scratch/emulator/usage-reports/runtime-status.txt`,
`.scratch/emulator/usage-reports/live-database-counts.txt`,
`.scratch/emulator/usage-reports/live-report.json`,
`.scratch/emulator/phase2/populated-report.json`, and
`.scratch/emulator/phase2/populated-report-authenticated-request.txt`. The
populated API response is real persisted data; a rebuilt parent APK visual
rendering remains a follow-up evidence item.

Safety events now pass through severity and age-band-sensitive routing before
the existing `PushSender`: younger bands receive medium-or-higher alerts,
TEEN receives high/critical alerts, OLDER_TEEN receives critical alerts,
quiet hours suppress non-critical alerts, and persisted dedupe keys plus a
five-per-parent-per-hour bound prevent noisy devices from spamming a parent.
Payloads contain only structured event metadata. Every routing outcome is now
persisted, including `QUEUED`, `SUPPRESSED_QUIET`, `SUPPRESSED_DEDUPE`, and
`SUPPRESSED_RATE`; the unique dedupe constraint was replaced with an indexed
lookup so suppressed attempts are retained. A live provider-independent run
is recorded in `.scratch/emulator/notifications/routing-request.txt` and
`.scratch/emulator/notifications/persisted-routing-outcomes.txt`. The current
sender is the provider-independent logging implementation; APNs/FCM delivery
and notification-provider credentials remain unavailable and are not claimed.

Phase 3 communication safety now includes an Android
`NotificationListenerService` scoped to an explicit communication-app
allowlist. Notification title/body values are consumed only in memory by a
deterministic weighted multi-signal rules detector and are not included in
events, persistence, logs, or parent UI. The detector requires contextual
co-occurrence, category-specific thresholds, communication metadata, and
hard-negative context guards; it emits self-harm, sexual content, sexual
solicitation, grooming, harassment, and phishing/credential-theft categories
with confidence derived from matched rule weights and a reason code. Only
category, severity, confidence, reason code, source package, and native
timestamp are bridged as structured events. Native deduplication (10 minutes)
and rate limiting (three events per 15 minutes) bound parent volume. iOS
reports `communication_risk_signals` as `UNAVAILABLE` because it has no
general notification-listener API. Parent/child surfaces are opt-in,
content-free, and expose permission-revocation recovery; iOS UI says
`Not available on iPhone/iPad`. Communication routing uses immediate critical,
high-priority, summary medium, and trend-only low dispositions.

The detector measurement now uses 120 genuinely unique labelled fixtures
(60 hard negatives and 60 positives), rather than counting repeated
executions of a smaller seed set:
60 hard negatives and 60 positives, including benign risk-word uses, quoted
lyrics, news, homework, medical, recipe/photo, school/sports/security
contexts, ambiguous single-word notifications, and two adversarial positives
per category that are intentionally expected to expose false negatives. The
focused native test was rerun after this carry-over and reported:

```text
SELF_HARM precision=1.0 recall=0.9 falsePositives=0 falseNegatives=1 adversarialMisses=self-harm-010
SEXUAL_CONTENT precision=0.9090909090909091 recall=1.0 falsePositives=1 falseNegatives=0 adversarialMisses=none
SEXUAL_SOLICITATION precision=1.0 recall=0.9 falsePositives=0 falseNegatives=1 adversarialMisses=none
GROOMING precision=1.0 recall=0.8 falsePositives=0 falseNegatives=2 adversarialMisses=grooming-009,grooming-010
HARASSMENT precision=1.0 recall=0.8 falsePositives=0 falseNegatives=2 adversarialMisses=harassment-009,harassment-010
PHISHING_CREDENTIAL_THEFT precision=1.0 recall=0.8 falsePositives=0 falseNegatives=2 adversarialMisses=phishing-009,phishing-010
uniqueFixtures=120 runtimeNanos=23123153 batteryMeasurement=UNAVAILABLE
```

The sole sexual-content false positive is the intentionally overlapping
`sexual-solicitation-005` case (`Trade an explicit photo with me`), which
the detector classified as sexual content rather than solicitation. The
documented adversarial misses are deliberate evidence of the rules'
limitations, not relabelled fixtures. Battery measurement is
`UNAVAILABLE`; runtime is not battery evidence. This is a curated
rules-based fixture measurement, not a production accuracy claim, and no
model or fabricated AI confidence score ships. Complete rerun output is
retained at `.scratch/emulator/reputation/communication-fixture-verification.log`
and in the native XML test report.

Phase 3 tablet/adaptive work now uses the cross-platform React Native
`useWindowDimensions` breakpoint at 600 points. Regular-width screens center
content at a maximum width of 720 points and use flexible two-column dashboard
sections; compact-width screens remain single-column. Parent Home and Activity
use the responsive dashboard container. A Pixel Tablet API 35 AVD
(`guardian-tablet-api35`, `emulator-5558`, 2560x1600) was booted and a fresh
parent account/family was authenticated through the real backend in the debug
development build. Actual Guardian Parent Home, Rules, Activity, and
Protection Health surfaces were captured in portrait:

- `.scratch/emulator/tablet-parent-home-portrait.png`
- `.scratch/emulator/tablet-parent-home-portrait.xml`
- `.scratch/emulator/tablet-parent-rules-portrait.png`
- `.scratch/emulator/tablet-rules-portrait.xml`
- `.scratch/emulator/tablet-parent-activity-portrait.png`
- `.scratch/emulator/tablet-activity-portrait.xml`
- `.scratch/emulator/tablet-parent-health-portrait.png`
- `.scratch/emulator/tablet-health-portrait.xml`

The same authenticated parent surfaces were captured in landscape:

- `.scratch/emulator/tablet-parent-home-landscape.png`
- `.scratch/emulator/tablet-home-landscape.xml`
- `.scratch/emulator/tablet-parent-rules-landscape.png`
- `.scratch/emulator/tablet-rules-landscape.xml`
- `.scratch/emulator/tablet-parent-activity-landscape.png`
- `.scratch/emulator/tablet-activity-landscape.xml`
- `.scratch/emulator/tablet-parent-health-landscape.png`
- `.scratch/emulator/tablet-health-landscape.xml`

An actual Child pairing surface was also rendered on the tablet in portrait:

- `.scratch/emulator/tablet-child-pair.png`
- `.scratch/emulator/tablet-child-pair.xml`

The parent authentication setup used a generated local test account; its
credentials are retained only in the ignored
`.scratch/emulator/tablet-auth-credentials.txt` artifact. iPad hardware or
simulator evidence and platform-native split-view evidence remain
unavailable; Expo Router Split View is iOS-only alpha and the shipped layout
therefore uses standard responsive primitives.

A code-level accessibility audit fixed the shared surfaces' focus semantics:
screen titles are headers, disabled buttons expose disabled state, status pills
are announced as one status, transient data-state messages use a polite live
region, and list-row labels/values can shrink and wrap instead of clipping at
large font scales. Shared controls retain the 44-point minimum touch target.
The node dump and screenshots under `.scratch/emulator/accessibility/` were
captured while the Expo development client remained on its confirmation
surface, so they are not claimed as authenticated parent/child rendering
evidence. TalkBack traversal, Dynamic Type rendering, contrast, reduced-motion,
and RTL checks still require device-level exercise on the product routes.

An emulator session was measured on child `emulator-5556` from
`2026-08-14T22:58:54Z` through `2026-08-14T22:59:15Z` with the VPN active on
`tun0`. The workload launched Guardian once and dispatched five URL intents
through Chrome while `dumpsys batterystats --reset` and
`dumpsys batterystats --checkin com.guardian.family` bracketed the session.
The URL intent `WaitTime` values were 497 ms, 26 ms, 61 ms, 38 ms, and 80 ms;
these are Android activity-dispatch timings, not isolated VPN/DNS decision
latencies. Guardian's warm `am start -W` reported `TotalTime: 0 ms` and
`WaitTime: 3 ms`, which is not a cold-start measurement. The VPN remained
connected after the workload. Raw output is at:

- `.scratch/emulator/performance/child-enforcement-session.txt`

The emulator battery report exposed no usable package CPU, radio, or energy
measurement (`-1`/unsupported power-profile fields and no package mAh
estimate), so battery cost is explicitly `UNAVAILABLE`, not inferred from
runtime. The native implementation now exposes dedicated counters and
duration averages through `GuardianProtection.getPerformanceMetrics()`:
VPN/DNS domain-decision count and average microseconds, policy-apply count and
average milliseconds, usage-refresh count and average milliseconds, native
bridge-event volume, and first module-startup timing. The child development
surface requests this snapshot in development builds without serializing
notification content. A live authenticated snapshot was captured:

```text
vpnDecisionCount=0
vpnDecisionAverageMicros=0
policyApplyCount=0
policyApplyAverageMillis=0
usageRefreshCount=0
usageRefreshAverageMillis=0
bridgeEventCount=0
moduleStartupMillis=332
batteryMeasurement=UNAVAILABLE_FROM_EMULATOR
```

The zero counters were a mount-time snapshot before the longer synchronization
path completed; `moduleStartupMillis=332` is the useful live startup measure.
The URL dispatch and warm-start numbers must not be used as proxies for these
paths.

The release app manifest was reconciled against the implemented code: camera,
internet, and vibration remain declared; unused microphone, external-storage,
and system-overlay permissions were removed. The main activity no longer
forces portrait orientation, allowing the responsive tablet layout to rotate
to landscape. Debug-only development manifests still retain the overlay
permission for the development client and are not release declarations. The
VPN, Accessibility, notification-listener, usage-access, and launcher-query
declarations remain because their corresponding native paths are implemented;
their user-consent and degraded-capability surfaces remain required.
The release manifest audit is recorded in
`.scratch/emulator/policy/release-manifest-audit.txt`; `:app:assembleRelease`
passed, and the packaged release declares only the implemented app/device
permissions plus the Guardian VPN, boot, usage-access, and biometric
dependencies. Its `MainActivity` has no fixed `screenOrientation`.

The Android policy audit found a reachable foreground-service failure on
Android 14+/target SDK 36: the VPN manifest declared the `specialUse`
foreground-service type, but `GuardianVpnService` used the two-argument
`startForeground` overload. Existing logs contained
`MissingForegroundServiceTypeException: Starting FGS without a type`. The
service now passes `ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE` on
Android 14+ and retains the two-argument call on older releases. Native unit
tests and the full debug APK build passed after the fix. The rebuilt APK was
installed on child `emulator-5556`, the app was relaunched through a live
development session, and the VPN recovered on `tun0`; no new
`MissingForegroundServiceTypeException` or VPN startup error appeared.
Evidence is at `.scratch/emulator/policy/foreground-service-type-fix.txt`.

The §21 observability review is recorded at
`.scratch/observability-review.md`. It covers structured events for policy
apply, enforcement decisions, VPN lifecycle, degraded capabilities, usage
collection, safety events, reputation synchronization, request/approval, and
notification routing, with timing, outcome, reason, and bounded counts where
available. Raw notification content and bridge-event JSON serialization are
excluded. Consistent request/correlation-ID propagation across native → JS →
API is implemented: requests accept or generate `X-Request-ID`, return it on
success and error responses, and mobile API errors retain the identifier.
Native bridge events carry a UUID correlation ID; child event ingestion
forwards it as the API request ID. A focused propagation test covers supplied
and generated request IDs. Structured log correlation and a native-to-API
end-to-end test remain follow-up verification.

The root setup and run guide is `README.md`. It was followed from a clean
shell with Node `v22.12.0`, pnpm `10.14.0`, uv `0.7.9`, frozen installs,
Alembic migration, root lint/typecheck/tests, PostgreSQL and backend
readiness. Compose uses `backend/docker-compose.yml` and the clean-shell PATH
includes `$HOME/.local/bin` for uv.

The §26/§27 interaction audit is archived at
`.scratch/emulator/interaction-audit/README.md`. It contains all 15 matrix
rows with actual tap counts where reachable, fixture-backed results for the
child and push rows, and screenshots for authenticated Home, Rules, Activity,
Health and Quick Control. Home now exposes signed add-time and pause actions.
The §26 inventory records the dedicated parent and child routes and their
links from overview surfaces.

The emulator edge-case probe is
`.scratch/emulator/interaction-audit/edge-case-probes.txt`. It verified three
connected AVDs, no third-party competing VPN package, process kill/relaunch,
and the clock/timezone capability probes. The emulator rejected timezone
property mutation and exposed no captive-portal control; multi-device,
guardian #2, reinstall/re-pair and clock/time mutation remain external
emulator/device acceptance actions. Populated child/push fixtures are archived
separately in `push-fixture-evidence.txt`.

The connected Android suite is counted in
`.scratch/emulator/interaction-audit/connected-test-count.txt`: two test
methods passed on each of the phone, child and tablet AVDs (six executions).
The pairing → signed policy → app block → child request → parent approval
sequence is exercised by the expanded instrumentation flow, with XML results
under `apps/mobile/modules/guardian-protection/android/build/outputs/androidTest-results/connected/debug/`.

The static OWASP MASVS v2.1.0/MASTG review is recorded at
`.scratch/owasp-mobile-code-review.md`, covering STORAGE, CRYPTO, AUTH,
NETWORK, PLATFORM, CODE, RESILIENCE (static-only), and PRIVACY (runtime
caveats). The Google Play Policy Insights workflow completed worker,
aggregation, critic, and compliance-report stages under
`.scratch/play_policy_insights_37a79f77-b6c9-4295-b00f-fa23573e90c5/`.
Material findings are documented rather than hidden: reviewer credentials are
needed for gated flows; the in-app account-deletion flow and public
`/account-deletion` route are now discoverable; and Data Safety must accurately
cover account, age-band/date-of-birth, child/app names, heartbeat/protection
metadata, and minimized safety events. Accessibility API, notification
listener, package visibility, and special-use foreground-service declarations
match the implemented release behavior, but reviewer evidence is still
required. The unpublished Play Store lookup returned 404 and is not a
compliance determination.

Account deletion is implemented through authenticated `DELETE /v1/auth/account`
with transactional family/child/device/event/policy/request/notification and
credential cleanup, an in-app parent confirmation, and public
`/account-deletion` information. Focused deletion, isolation, repeated-delete,
and route-inventory tests cover the path. The source-of-truth Data Safety
declaration is `docs/DATA_SAFETY_DECLARATION.md`; capability disclosures name
VPN, Accessibility, notification access, and Usage Access before opening the
corresponding settings.

Final authenticated accessibility artifacts are captured under
`.scratch/emulator/accessibility/` for parent Home/Rules/Activity/Health and
child Home/My Time/block surfaces. The source audit fixes the collapsed
ScrollView accessibility node, explicit labels/roles, minimum touch targets,
wrapping at large text, opacity-only press feedback, and no custom motion.
TalkBack traversal, contrast measurement, and physical-device Dynamic Type
remain limited to the Android emulator/session evidence; RTL and reduced
motion source/configuration checks are recorded, while iOS Dynamic Type and
physical accessibility acceptance remain external.

The end-to-end native → JavaScript → API correlation run is recorded in
`.scratch/emulator/correlation-webblocked-final.log`: the same
`WEB_BLOCKED` correlation IDs appear in native `GuardianEvents`, the
ReactNativeJS payload, and backend `POST /v1/devices/me/events` structured
logs. Backend lines include both request and response request IDs. The
request client now preserves a supplied native `X-Request-ID` instead of
overwriting it.

Non-zero enforcement evidence is recorded in
`.scratch/emulator/performance/nonzero-enforcement-logcat.txt` and
`.scratch/emulator/performance/nonzero-enforcement-final.txt`; the run
includes policy apply, usage refresh, bridge events, startup and VPN/DNS
decision counters after synchronization. Emulator `dumpsys batterystats`
exposed no usable package energy value, so no mAh estimate is claimed.

The local PRD gaps from the previous checkpoint are closed. Parent Home now
mutates signed `TEMPORARY_SCREEN_TIME` and `PAUSE_INTERNET` policies, the Android
evaluator applies active DEVICE time extensions and STRICT pause routines, and
MORE_TIME approval produces a signed DEVICE override. Dedicated §26 routes and
child time/rules routes are present and linked from their overview surfaces.
The refreshed §26/§27 evidence is under
`.scratch/emulator/interaction-audit/`, including the agent-device Home action
capture and populated push fixture evidence.

Remaining claims are external gates only: iPad hardware/simulator and native
split-view (Mac/Xcode), iOS compilation and Family Controls/Network Extension
entitlements, APNs/FCM provider credentials and delivery, physical-device
performance/battery/accessibility, Play reviewer credentials/store approval,
and an independent production-labelled communication-safety evaluation.

## Final reconciliation sweep

The final local verification pass completed after the reconciliation commits:

```text
root lint: passed
root typecheck: passed
root tests: 6 files, 60 tests passed
mobile lint: passed
mobile typecheck: passed
mobile Jest: 7 suites, 27 tests passed
backend Ruff: passed
backend mypy: 59 source files, no issues
backend pytest: 117 passed
Alembic empty PostgreSQL database upgrade: passed to head
Kotlin unit tests: BUILD SUCCESSFUL
Android debug + release + connectedDebugAndroidTest: BUILD SUCCESSFUL
OpenAPI drift: passed after refreshing packages/api-client/src/generated.ts
```

The marker search found no production TODO/FIXME/stub/mock markers. Its
seven matches are numeric comparisons containing the word “placeholder”, an
iOS storyboard framework placeholder, or PRD/checkpoint documentation
discussing placeholders; none is executable Guardian product logic.
Ruff unused-import/unused-assignment checks passed as the dead-code smoke
check. The checked-in root `README.md` setup/build/run instructions were
followed from a clean shell; Android Gradle builds, connected tests, live
Metro, backend readiness and all three emulator connections were verified.
