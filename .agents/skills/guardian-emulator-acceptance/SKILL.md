---
name: guardian-emulator-acceptance
description: How to bring up and end-to-end test the Guardian parent/child family-safety app on Android emulators (policy sync, domain blocking, app time limits, offline enforcement, protection health). Use when running acceptance/regression testing of the guardian repo on emulators.
---

# Guardian emulator acceptance testing

## Bring-up (all of this is required; nothing survives a machine restart)
1. `docker compose -f backend/docker-compose.yml up -d postgres`
2. Backend: `uv run --directory backend uvicorn app.main:app --host 0.0.0.0 --port 8000`
   with `GUARDIAN_POLICY_PRIVATE_KEY` from `scripts/generate-policy-key.py`
   (key id `guardian-dev`). Verify `curl :8000/readiness` → `{"status":"ready"}`.
3. Metro: `npx expo start --port 8081` in `apps/mobile`.
4. Emulators (`guardian-api35` = parent, `guardian-api35-child` = child).
   `sudo -n chmod 666 /dev/kvm` if KVM fails.
5. The debug APK must be built with the SAME public key the backend signs with,
   otherwise the child rejects every bundle. Rebuild if the backend key changed OR
   if any Kotlin code changed (JS comes from Metro, native does not):
   ```
   cd apps/mobile/android
   export ANDROID_HOME=$HOME/android-sdk ANDROID_SDK_ROOT=$HOME/android-sdk
   export GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS='{"guardian-dev":"<base64 pubkey>"}'
   ./gradlew assembleDebug   # then adb install -r app/build/outputs/apk/debug/app-debug.apk
   ```
   Forgetting `GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS` bakes `{}` into BuildConfig; the
   symptom is child home showing "Web protection is unavailable." plus a LogBox
   `Reputation bundle rejected: SIGNATURE_INVALID`, and because `syncReputation()`
   runs BEFORE `acknowledgePolicy` in `child/home.tsx` the device also stops acking
   policies. Derive the public key from the backend `GUARDIAN_POLICY_PRIVATE_KEY`.
   Reinstalling the APK also signs the parent app out — recover the parent email from
   `select email from parents;` before re-signing in.
6. Per emulator: `adb -s <serial> reverse tcp:8081 tcp:8081` and
   `adb -s <serial> reverse tcp:8000 tcp:8000`.

## Permissions the child device needs (grant via adb, equivalent to user consent)
```
adb -s <child> shell appops set com.guardian.family ACTIVATE_VPN allow
adb -s <child> shell appops set com.guardian.family GET_USAGE_STATS allow
# app blocking (block surface) requires the accessibility service:
adb -s <child> shell settings put secure enabled_accessibility_services \
  com.guardian.family/expo.modules.guardianprotection.accessibility.GuardianAccessibilityService
adb -s <child> shell settings put secure accessibility_enabled 1
```
`am force-stop com.guardian.family` unbinds the accessibility service, so
`app_blocking` drops to UNAVAILABLE until the app is reopened — expect health to
report DEGRADED then. Notification-listener consent is normally never granted in
tests, so DEGRADED is the honest steady state; do not treat DEGRADED alone as
proof that a revocation test worked — compare the `capabilities` JSON in
`protection_health_events` before/after.

## Traps that make tests look broken when they are not
- **Bedtime routine**: the default TEEN policy has a `SCHEDULED` `bedtime-teen`
  routine 22:00–06:00 with `web_mode: STRICT`. If host/emulator time falls in that
  window, *everything* web is blocked and domain-rule tests are unattributable.
  Fix by deleting the routine from parent Rules (bottom of the screen) or by
  giving the child profile a timezone where the current UTC time is daytime.
  Do NOT change the emulator clock: device requests are signed with
  timestamp/nonce validation, so clock skew silently breaks policy ack/heartbeat
  (device stops acking, `devices.policy_version_applied` freezes).
- After adding a new blocked domain the VPN interface restarts; the first Chrome
  navigation may show `ERR_NETWORK_CHANGED`. Reload once before judging.
- **Chrome cache makes a blocked domain look allowed.** Re-loading a previously visited
  URL (e.g. `https://example.org`) can render from Chrome's cache even though the VPN is
  dropping the traffic, which looks like a total enforcement failure. Always re-test with a
  cache-busting query (`https://example.org/?nc=<random>`); a real block shows
  `ERR_NETWORK_CHANGED` / `ERR_CONNECTION_*`. Corroborate with the child's
  `GUARDIAN_PERFORMANCE_METRICS_AFTER_SYNC` log line: `vpnDecisionCount` stays 0 when no
  traffic actually reaches the tunnel.
- `adb shell ping <blocked domain>` may succeed even when enforcement works (shell uid is
  outside the VPN's per-app routing and IPs of test domains rotate). Judge domain blocking
  from Chrome, not from shell ping.
- If parent screens show "This data may be out of date.", the parent session has expired:
  parent write actions (Rules buttons, "Add 15 minutes") then silently no-op and no new
  `policy_bundles` row appears. Sign the parent back in before concluding the child stopped
  syncing.
- Selective routing means only resolved IPs of blocked domains are tunneled;
  a blocked domain fails DNS (`ping: unknown host`) while others work.
- The parent Rules app list is long and re-sorts as new apps are observed;
  the "Daily limit minutes" field is at the END of the app list and applies to
  every "Limit to N minutes" button. Set it first, then tap the app's button.
- Typing with the computer-use `type` action often does not reach emulator text
  fields; use `adb -s <serial> shell input text ...` (and `input keyevent KEYCODE_DEL`).

## Useful verification queries (psql in the postgres container)
```
select policy_version_applied, protection_state, last_seen_at from devices where child_profile_id='<id>';
select policy_version, jsonb_pretty(new_value) from policy_bundles where child_profile_id='<id>' and is_current;
select request_type, state, reason, subject, created_at from requests where child_profile_id='<id>' order by created_at desc;
select app_ref, duration_seconds, occurred_at from usage_aggregates where device_id='<child device id>' order by occurred_at desc;
```
Since PR #3 parent "Activity" "Today's usage" aggregates the CHILD's backend usage points
(`aggregateTodayUsage` over `GET /v1/families/{id}/activity/usage`). Beware: each child
upload appends a NEW row carrying the cumulative daily total, and the aggregation SUMS all
of today's rows — so after N uploads every figure is roughly N× the truth. Force a second
upload (force-stop + relaunch the child) before trusting these numbers, and cross-check
`usage_aggregates` rows against the child's own "My time".

## Screen-time numbers: how to check UI vs enforcement
The native usage summary keys are prefixed (`APP:<pkg>`, `CATEGORY:<c>`, `DEVICE`).
Since PR #3 child `time.tsx` reads `byTarget["APP:"+app_ref]` and `totalSeconds` is the
`DEVICE` bucket only; per-app remaining then decrements with real use and flips to
"No time left today." when native reports `APP_BLOCKED · BUDGET_EXHAUSTED`. If a future
regression reappears (constant remaining, or a device headline ~3× the real total), suspect
the prefix lookup / `totalSeconds` again. Always trust the native decision (block surface /
`APP_BLOCKED` events) over the remaining-minutes text and cross-check against the per-app
foreground seconds you derive from `usage_aggregates`.

## Temporary grants (MORE_TIME approvals)
- Subject matching an existing `app_rules[].app_ref` → APP grant, `existing + 15` minutes;
  a subject that parses as a domain → `DOMAIN`/`ALLOW`; empty subject → `DEVICE`
  (`base budget + 15`). Verify with
  `select jsonb_pretty(new_value->'temporary_overrides') from policy_bundles ... is_current`.
- MORE_TIME grant TTL is hardcoded to 1 hour, and the parent "Add 15 minutes" quick action
  is DEVICE-scoped with a 15-minute TTL, so **natural expiry of an app-scoped grant cannot
  be observed in a short run** without changing the clock (which is forbidden). Use the
  15-minute device grant disappearing from child "My time" as the expiry-filtering proxy.
- The child must be foregrounded (or navigated back to child home) to fetch + apply a new
  bundle; resuming onto a sub-screen does not sync.
- App rules used to ACCUMULATE (first match won, so a tight limit could never be loosened).
  Since PR #4 parent writes REPLACE the rule for that target and the evaluators take the
  LAST matching app/category rule (domains: most specific, ties by write order), so
  loosening from Rules works: verify with
  `select policy_version, jsonb_path_query_array(new_value->'app_rules', '$[*] ? (@.app_ref == "com.android.chrome")') from policy_bundles where child_profile_id='<id>' order by policy_version desc limit 2;`
  and expect exactly ONE Chrome rule per bundle. Legacy bundles that still carry duplicate
  rules resolve to the last one. If loosening seems not to work, check the parent session
  first (expired session silently no-ops writes) — no new `policy_version` row means the
  write never happened.
- **Verify the child accessibility service is still enabled right before judging any
  app-blocking assertion.** It can end up disabled mid-run (`settings get secure
  accessibility_enabled` → `0`, `enabled_accessibility_services` → `null`, e.g. after
  force-stops/relaunch loops or a manual workaround). Symptom: child "My time" says
  "No time left today." but Chrome opens normally — this looks exactly like an enforcement
  bug. Re-enable both settings and retry before reporting. Parent → Protection health does
  report this honestly (`DEGRADED`, Protection status Active `No`, Health `DISABLED`,
  missing `app_blocking`), so use that screen as the tiebreaker.
- UsageStats/native budget accounting lags the UI by up to ~1-2 min: after the native
  "Time is up" surface appears, "My time" may still show `1 minutes remaining.` for a beat
  (and vice versa). Re-open the screen after ~60 s (relaunch the child app to force a fresh
  summary + upload) before declaring UI/native disagreement.

## Devin Secrets Needed
None (local dev signing key is generated on the box).
