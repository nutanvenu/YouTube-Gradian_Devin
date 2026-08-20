# Guardian Android consumer MVP — implementation and validation report

Date: 2026-08-16  
Branch: `codex/android-consumer-mvp-content-safety`  
Base: `900ef272fa51369f075ecd1ed38cb26f0918d355`  
Final implementation head covered by this report: `332f4a4`

## Outcome

Guardian now has a production-minded consumer-Android safety foundation: accurate
daily usage snapshots, resilient policy/session synchronization, source-tagged
partial app inventory, a local deterministic content-risk pipeline, exact
15-minute content approvals, a recoverable native block surface, and release
admission that rejects debug signing and unsafe production inputs.

Every product defect reproduced in the executable backend, TypeScript, and
React Native layers was fixed and regression-tested. This is **not** a release
or Play-approval claim. Kotlin/JVM execution, APK construction, connected
instrumentation, and the two-emulator acceptance journeys could not be run on
this host. The root filesystem remained approximately 100% full and the local
API 35 AVD definitions had no usable system image. No APK, screenshot, or
device-runtime evidence was fabricated.

No deployment, publication, push, production secret, production signing key,
real child data, or destructive change to the original checkout was performed.

## Isolation and repository boundaries

- Original repository checkout: `/media/dikshith/D Drive2/Delta IV/Sofwares/Guardian App`
- Isolated implementation worktree: `/media/dikshith/D Drive2/Delta IV/Sofwares/Guardian App Worktrees/android-consumer-mvp-content-safety`
- User fork remote: `git@github.com:ThisIsDikshithPodhila/YouTube-Gradian_Devin.git`
- Upstream remote: `git@github.com:nutanvenu/YouTube-Gradian_Devin.git`
- Nothing was pushed. The original worktree and unrelated user data were preserved.

## What now works

### Correct parent/child control loop

- Cumulative Android usage is upserted as one current daily snapshot instead
  of repeatedly appended and summed. App/category/device hierarchy is
  reconciled without double counting; unmatched roll-up time is explicit.
- Parent access refresh is single-flight and retried once. An unrecoverable
  session becomes an actionable `SESSION_EXPIRED` state without erasing the
  paired child identity.
- Reputation synchronization is isolated from policy acknowledgement,
  heartbeat, usage, inventory, and parent controls.
- Parent mutations and approvals use consistent database locking and
  resource-bound idempotency, preventing lost policy updates or broad fallback
  grants.
- App-rule drafts are keyed by package and remain stable when inventory order
  changes; each app's limit control is adjacent to its actions.

### Privacy-constrained content safety

- One local pipeline performs observation, normalization, deterministic
  classification, policy thresholding, verdict, enforcement, and minimized
  event creation.
- Notifications are app-agnostic for opted-in user apps. Guardian/system noise,
  OTP/authentication, financial-sensitive notifications, and media controls are
  excluded before classification.
- Accessibility text is read only after local affirmative consent and a usable
  signed policy explicitly enables the signal. Processing is limited to the
  active window on meaningful events, debounced, bounded to 80 nodes/20 ms/
  1,200 characters, and excludes editable/password nodes.
- Unicode compatibility normalization, contextual education/news suppression,
  safety negation, severity/confidence, canonical reason codes, and a
  replaceable `ContentRiskClassifier` interface are implemented. The provider
  is explicitly deterministic rules, not production ML.
- Only the minimized verdict tuple is persistable or transportable. Raw
  notification text, Accessibility text, trees, URLs with queries, icons,
  screenshots, and packet bodies are absent from the contracts.

### Recoverable blocking and exact approval

- Foreground Accessibility `BLOCK_AND_REQUEST` findings can create a native
  interstitial with **Ask parent**, **Go back**, and **Close app/Home** actions.
- Settings, launcher/system packages, updated-system apps, emergency/system
  paths, and Guardian itself are excluded from content blocking.
- A block persists for the exact device + app + keyed content fingerprint.
  Changed content is independently classified; complete `WARN`/`ALLOW` content
  releases the previous item, while partial/blank/unavailable reads cannot.
- Only an explicit Ask parent action queues a deduplicated encrypted
  `CONTENT_REVIEW`; offline requests never unlock locally.
- Approval is idempotent, tuple-bound, and expires exactly 15 minutes after the
  decision. A changed fingerprint or another app/device remains blocked.

### Honest inventory, VPN, and capability state

- Inventory combines LauncherApps with packages observed through UsageStats,
  notifications, VPN attribution, and Accessibility foreground identifiers.
  It remains explicitly `PARTIAL`; `QUERY_ALL_PACKAGES` is not added.
- Package ID, name, category, version, first/last seen, install/visibility
  state, observed usage, policy/risk state, and source metadata flow through
  the child upload and parent API. Icons and content do not.
- Inventory refreshes when the child app returns to foreground, so lifecycle
  changes are not restricted to one process-mount upload.
- The VPN no longer forwards DNS to hard-coded plaintext UDP/53. The DoH path
  uses a protected socket, pre-TUN bootstrap, TLS hostname verification/SNI,
  bounded DNS-message POST, and no plaintext fallback.
- Permission/service/policy state is capability-gated. A stopped but authorized
  VPN shows a Retry web protection action. Policy-disabled Accessibility is
  explained to the child and does not misleadingly offer local consent controls.

### Release safeguards

- Release tasks require explicit non-debug signing, certificate digest,
  canonical Ed25519 policy trust anchors, real HTTPS API/DoH endpoints, positive
  version code, and fixture mode disabled.
- Release output no longer uses debug signing. Compile/target SDK is 36.
- Backup and cleartext are disabled for release; debug cleartext is scoped to
  local emulator endpoints.
- APK/AAB verification code checks effective manifests, signers, version code,
  monitoring metadata, prohibited permissions, and fixture markers.
- Production backend secrets stay server-side and fail closed in production.

## Reproduced defects, root causes, and fixes

| Defect | Root cause | Fix/evidence |
| --- | --- | --- |
| Repeated usage uploads inflated parent totals | Cumulative counters were appended and hierarchy levels were summed together | Daily snapshot upsert, hierarchy reconciliation, migration `0020`; backend regressions cover repeat/lower/different-device/timezone cases |
| Activity silently omitted sources beyond 500 | SQL limited raw rows before hierarchy resolution | Resolve the full bounded seven-day window; 501-app regression |
| Legacy invalid timezone broke migration | Direct `AT TIME ZONE` accepted unchecked stored values | Validate new IANA values and use deterministic UTC migration fallback |
| Reputation failure prevented unrelated protection sync | Reputation call sat in the critical awaited sequence | Isolated advisory sync and explicit degraded state |
| Shipping example reputation looked authoritative | Production seed classifier invented curated fixture data | Removed seed; honest UNKNOWN provider placeholder |
| Expired parent sessions silently no-op/raced | Per-request refresh and broad storage clear | One refresh, single-flight, actionable signed-out state, separate parent/device identity clearing |
| Concurrent policy/approval writes lost changes | Bundle was read before the policy-document lock | Locked read-modify-sign-write and resource-scoped idempotency |
| Unmatched request could become device-wide approval | Free-form subject fallback widened scope | Exact subjects only; only explicit null MORE_TIME is device-wide |
| App-rule UI reordered or applied the wrong limit | Shared draft state and mutable inventory order | Package-keyed drafts and stable copied sort |
| Content approval was broad and one hour | Temporary policy override/free-form subject | Separate exact content approval tuple, decision +15 minutes |
| Content contracts could accept raw/arbitrary data | Loose metadata/reason fields | Strict Pydantic/OpenAPI/TS/Kotlin minimized schemas and canonical enums |
| Notification monitoring depended on JS/static allowlist | Listener delegated to a transient JS bridge | Native cold-start policy/runtime and app-agnostic privacy filter |
| Accessibility could inspect without a complete consent chain | Manifest/runtime gate did not align | Local disclosure consent + verified signed policy before any window read |
| Partial Accessibility traversal could unlock risk | Truncation was indistinguishable from a safe result | Extraction completeness bit; partial/blank results cannot clear blocks |
| Changed medium-risk content remained stuck behind old block | Only `ALLOW`, not `WARN`, cleared the prior tuple | Every complete non-blocking verdict clears; Luna closure review passed |
| Background notification could create a later app block | Foreground relevance was not signal-specific | Notification verdicts persist evidence only; Accessibility foreground drives blocks |
| Block surface lacked live recovery | Native interstitial had no complete recovery/ask flow | Ask parent, Back, Close/Home, exact reblock, >=48dp actions |
| Inventory claimed too little/grew stale | Lifecycle/source metadata was dropped and upload was one-shot | Source-tagged partial lifecycle contract, migration `0022`, foreground refresh |
| Clean install failed at migration `0022` | Revision ID exceeded Alembic's 32-character version column | Shortened revision ID; fresh PostgreSQL inventory suite passes 4/4 |
| Capability UI implied Accessibility was usable when parent policy disabled it | UI checked consent/permission but not the signed-policy capability | Native policy-aware capability plus child explanation; Luna closure review passed |
| Accessibility declaration denied screen-content access while the consented runtime inspects exposed labels | Release metadata described older foreground-app-only behavior | Manifest and parent disclosures now state bounded local active-window inspection, exclusions, and immediate raw-text discard |
| Authorized but stopped VPN had no recovery action | Button was shown only for missing permission wording | Preserve actionable LIMITED state and show Retry web protection |
| Release could be debug-signed or point at placeholders | Release reused debug config and had no artifact admission | Explicit release-only signing and final-artifact validators |

## Changed interfaces and data model

- Signed policy: optional `content_safety.content_block_threshold`, with legacy
  age defaults of MEDIUM/MEDIUM/HIGH/CRITICAL for young child/preteen/teen/
  older teen. Existing notification alert threshold remains independent.
- Requests: strict `CONTENT_REVIEW` evidence with app reference, 64-hex keyed
  fingerprint, category, severity, confidence, reason code, and optional public
  content reference.
- Approvals: `ContentApproval` keyed by device/app/fingerprint, with exact active
  device-authenticated delivery and 15-minute decision-based expiry.
- Events: minimized content verdict fields and hostname-only domain metadata.
- Inventory: version, first/last seen, install/visibility state, capability
  sources, and `PARTIAL` completeness added through migration `0022` and OpenAPI.
- Android native module: consent, minimized outbox, approval application,
  protection/capability state, source-tagged inventory, and native block events.

## Validation evidence

All exit results below are from the isolated worktree on 2026-08-16.

| Command/check | Exit/result | Classification |
| --- | ---: | --- |
| `corepack pnpm test` | 0; 6 files / 67 tests | CONFIRMED package contracts/policy |
| `corepack pnpm lint` | 0 | CONFIRMED static JS/TS |
| `corepack pnpm typecheck` | 0 | CONFIRMED root TypeScript |
| `corepack pnpm --dir apps/mobile test --runInBand` | 0; 9 suites / 63 tests | CONFIRMED mocked mobile UI/client/state |
| `corepack pnpm --dir apps/mobile lint` | 0 | CONFIRMED mobile static |
| `corepack pnpm --dir apps/mobile typecheck` | 0 | CONFIRMED mobile TypeScript 6 |
| `JAVA_HOME=... corepack pnpm --dir apps/mobile test:release-admission` | 0; 17/17 | CONFIRMED source/admission policy |
| `backend/.venv/bin/python -m pytest backend/tests -q` | 0; 160 passed in 34.68s | CONFIRMED backend + fresh migrated PostgreSQL fixtures |
| `backend/.venv/bin/python -m pytest backend/tests/test_inventory.py -q` against fresh tmpfs PostgreSQL | 0; 4 passed | CONFIRMED migration `0022` and inventory API |
| `backend/.venv/bin/python -m ruff check backend` | 0 | CONFIRMED Python static |
| `backend/.venv/bin/python -m mypy backend/app` | 0; 60 source files | CONFIRMED backend typing |
| Direct OpenAPI generation + `git diff --exit-code -- packages/api-client/src/generated.ts` | 0 | CONFIRMED generated client has no drift |
| `corepack pnpm check:openapi` wrapper | 1; nested script could not find bare `pnpm` | ENVIRONMENT; direct canonical generator above passed |
| Manifest/prohibited-permission/private-key regex scan | 0; no prohibited release hits or private-key blocks | CONFIRMED static negative scan, not a binary scan |
| `corepack pnpm audit --prod --audit-level high` | 1; 2 high + 2 moderate | FAILED dependency gate; see residual risks |
| Kotlin `:guardian-protection:testDebugUnitTest` | no task XML; Gradle stalled/previously hit ENOSPC before task execution | UNVERIFIED environment |
| Debug APK with backend-matching policy key | no artifact | UNVERIFIED environment |
| Connected instrumentation | not executed | UNVERIFIED environment |
| `guardian-api35` + `guardian-api35-child` acceptance | not executed; usable API 35 system image unavailable | UNVERIFIED environment |

The backend test database was an isolated PostgreSQL 16 container with tmpfs
storage. It was stopped and removed after the run. No production or user data
was used. Test logs establish schema/API behavior; they are not device evidence.

### Synthetic classifier metrics

The golden resource contains 140 synthetic/public cases: 130 evaluable and 10
explicitly unavailable custom-rendered cases. A host-side mirror of the checked-in
normalizer/rules produced the following. These numbers are a deterministic
fixture regression result, **not real-world accuracy**; the Kotlin evaluator
that consumes the same dataset remains unexecuted on this host.

| Category | Precision | Recall | False positives | False negatives | Frozen baseline precision | Frozen baseline recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ADULT_NUDITY | 1.000 | 1.000 | 0 | 0 | 0.938 | 0.833 |
| DANGEROUS_CHALLENGE | 1.000 | 1.000 | 0 | 0 | 0.952 | 0.870 |
| SELF_HARM_SUICIDE | 1.000 | 1.000 | 0 | 0 | 0.714 | 0.882 |
| WEAPONS | 1.000 | 1.000 | 0 | 0 | 0.833 | 0.833 |

The fixture app is non-shipping and can present safe, medium/high risk,
negated, educational/news, Unicode-obfuscated, and inaccessible Canvas content;
change content in-app; emit equivalent notification/media metadata; open test
domains; and simulate foreground/background transitions.

## Emulator/device evidence matrix

| Target | Result | Evidence/limit |
| --- | --- | --- |
| Host contracts/mobile/backend | CONFIRMED | Commands above |
| Android Kotlin/JVM | UNVERIFIED | No completed Gradle task or test XML |
| Debug APK/API 36 build | UNVERIFIED | No artifact; disk/toolchain setup failed before build |
| `guardian-api35` parent | UNVERIFIED | AVD definition only; no usable system image/run |
| `guardian-api35-child` child | UNVERIFIED | AVD definition only; no usable system image/run |
| Additional Android API levels | UNVERIFIED | No runnable emulator matrix |
| Physical Android | UNVERIFIED | No device supplied |
| Play Console/review | UNVERIFIED | No upload or policy review requested/performed |

Screenshots are therefore unavailable. Source checks, unit/component logs, and
disposable-database results must not be interpreted as proof of touch behavior,
Android service lifecycle, p95 latency, or store eligibility.

## Requirement status

| Requirement | Status | Evidence or remaining boundary |
| --- | --- | --- |
| Accurate repeated daily usage totals | CONFIRMED | Backend migration/API/report regressions |
| Reputation outage isolation | CONFIRMED | Backend/mobile regressions |
| Expired parent session recovery | CONFIRMED | Client/server concurrency tests |
| Stable per-app rule controls | CONFIRMED | Mobile component tests |
| Strict minimized content contracts | CONFIRMED | Backend/OpenAPI/TS tests; raw canary rejection |
| Age-default and parent-overridden content block threshold | CONFIRMED | Signed policy/contract tests |
| Exact 15-minute backend content approval | CONFIRMED | Backend tuple/dedupe/expiry/concurrency tests |
| App-agnostic notification classification | PARTIAL | Native source/tests exist; JVM/device execution unverified |
| Consent-gated active-window Accessibility classification | PARTIAL | Bounds/gates reviewed; device execution unverified |
| Native recoverable block interstitial | PARTIAL | Source/pure regressions reviewed; UI/device behavior unverified |
| Same-content reblock and changed-content reclassification | PARTIAL | State logic/review passed; emulator lifecycle unverified |
| Live online parent resolution p95 <=3 seconds | FAILED | Current child approval fetch is opportunistic; no production push/native authenticated live channel |
| Offline request never unlocks | PARTIAL | Fail-closed state logic exists; device/network transition unverified |
| Partial lifecycle-aware inventory without `QUERY_ALL_PACKAGES` | PARTIAL | Backend/mobile confirmed; native PackageManager/device lifecycle unverified |
| DoH encrypted DNS transport/no plaintext fallback | PARTIAL | Static design checks pass; live resolver/TLS/VPN handshake unverified |
| Honest permission/force-stop/reboot/VPN state | PARTIAL | Capability/UI logic tested; actual reboot/force-stop/competing VPN unverified |
| Debug signing rejected for release | CONFIRMED for admission | Actual signed APK/AAB verification unverified because no artifact |
| Raw content absent from contracts/backend/JS transport | CONFIRMED | Strict schemas, raw canary and source scans |
| Raw content absent from real device logs/storage/HTTP/crashes | UNVERIFIED | Requires built APK, emulator traffic/log/database/storage inspection |
| TalkBack, large text, reduced motion, contrast, >=48dp touch targets | PARTIAL | 48dp source implementation; device accessibility inspection unverified |
| Golden >=100-case regression dataset | CONFIRMED as fixture | 140 cases; native evaluator execution unverified |
| Chrome/fixture domain blocking with VPN evidence | UNVERIFIED | No runnable emulator/APK |
| Pairing and critical two-emulator parent/child journeys | UNVERIFIED | No runnable emulator/APK |
| Dependency vulnerability gate | FAILED | Expo/Metro transitive `image-size@1.2.1` advisories have no patched version in audit metadata |
| Google Play approval/universal third-party visibility | UNVERIFIED/UNAVAILABLE | Requires Play review; Android signals remain app/platform-dependent |

## Security, privacy, and policy review

- No root, Device Owner, MDM, factory reset, TLS interception, root CA,
  MediaProjection, keylogging, click-history recording, continuous screenshots,
  message storage, packet-body upload, hidden icon, or stealth mode was added.
- No `QUERY_ALL_PACKAGES` was added. Package visibility remains source-gated and
  explicitly partial.
- Main/exported components are limited to the launcher and Android-bound
  services whose permissions define their entry boundary. Final merged-binary
  inspection remains part of the unexecuted APK gate.
- `pnpm audit` identifies two high and two moderate advisories through Expo
  Metro's transitive `image-size@1.2.1`. The registry reported no patched
  version. This is primarily a developer/bundler parser exposure, but it remains
  a failed release dependency gate. Do not force an unsupported SDK override;
  track the Expo/Metro remediation or vendor-reviewed containment before release.
- Google Play still requires package-visibility minimization, monitoring-tool
  `child_monitoring` disclosure, prominent Accessibility disclosure/consent,
  and Families/child-safety review. Source compliance does not equal approval.

Official review references:

- Package visibility: https://support.google.com/googleplay/android-developer/answer/10158779
- Monitoring tools: https://support.google.com/googleplay/android-developer/answer/12955211
- Accessibility APIs: https://support.google.com/googleplay/android-developer/answer/16558241
- Families policy: https://support.google.com/googleplay/android-developer/answer/9893335
- MediaProjection consent: https://developer.android.com/media/grow/media-projection

## Residual risks and external validation required

1. Provide sufficient build-host disk, the pinned Node 22.13 toolchain, JDK 17,
   Android SDK/build-tools 36, and a usable API 35 system image.
2. Run Kotlin/JVM tests, build the debug APK with the exact backend public key,
   inspect the effective APK/AAB manifest/signature, and rerun dependency gates.
3. Run connected instrumentation and the complete two-emulator matrix,
   collecting screenshots, logcat, local encrypted-store/database inspection,
   HTTP/VPN evidence, rotation/recents/reboot/rapid-switch tests, and p95 timing.
4. Add a production-grade, authenticated native approval delivery provider if
   the <=3 second online target remains an MVP requirement. The current logging
   push sender/in-process broadcaster cannot establish that SLA.
5. Validate DoH/TLS, QUIC/DoH bypass limitations, unknown attribution, captive
   portal, competing VPN, and OEM background restrictions on physical devices.
6. Resolve or formally accept the Expo/Metro `image-size` advisories before any
   release candidate.
7. Obtain Google Play policy review. Encrypted payloads, inaccessible custom/
   Canvas views, and apps that hide metadata must remain BEST_EFFORT or
   UNAVAILABLE in product wording.

## Business intent and what we have unlocked

The business objective is broad, transparent protection that families can
trust—not spyware and not a demo that overstates Android visibility. The work
now gives Guardian a coherent consumer-MVP control plane: trustworthy activity
totals, resilient signed policy, privacy-minimized local detection, exact
item-level parental review, recoverable blocking, and honest capability state.

What we have unlocked is a credible path to a shippable family-safety product:
the data contracts and backend control loop are validated, Android enforcement
is modular and app-agnostic where the OS provides signals, and release admission
fails closed. The remaining work is concentrated and visible—native build/
device acceptance, real-time approval delivery, dependency remediation, and
Play/physical-device review—rather than hidden behind green unit tests.
