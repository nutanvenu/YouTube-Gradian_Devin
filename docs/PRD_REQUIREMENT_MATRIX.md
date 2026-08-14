# Guardian PRD requirement matrix

Reviewed against `docs/Guardian_Master_PRD.md` from the first line through
§40. This is an implementation and evidence inventory, not a declaration that
the product is release-ready. “Unverifiable here” means that source and local
emulators are insufficient evidence for the PRD requirement.

## Status key

| Status | Meaning |
| --- | --- |
| Implemented | The requirement has an implementation and local verification evidence. |
| Partially implemented | A meaningful slice exists, but one or more PRD behaviors, platforms, or acceptance conditions remain. |
| Unimplemented | The repository does not yet provide the required behavior. |
| Unverifiable here | The behavior may be implemented or scoped, but required external evidence is unavailable in this Linux/emulator environment. |

## Matrix

| PRD requirement | Implementation location | Verification evidence | Status | Gap / exact external action |
| --- | --- | --- | --- | --- |
| §0.1, §3.2 one app with persisted, device-bound parent/child roles | `apps/mobile/src/app/role-selection.tsx`, `src/state/role.ts`, parent/child route groups | Mobile tests; authenticated parent and child emulator routes under `.scratch/emulator/accessibility/` | Partially implemented | Physical acceptance must verify role binding cannot be bypassed after reinstall or account changes. |
| §0.1, §3.5, §20 privacy-first local enforcement and no raw content upload | Android notification/accessibility runtimes; `apps/mobile/src/api/client.ts`; `docs/DATA_SAFETY_DECLARATION.md` | `.scratch/runtime-owasp/runtime-checks.txt`; native communication tests; source audit | Implemented | Physical-device and store-review privacy testing still required. |
| §0.1, §3.6 no TLS MITM | `GuardianVpnService.kt` DNS forwarding/filtering path; no CA installation | `.scratch/owasp-mobile-code-review.md`; release manifest audit | Implemented | Verify on a physical device and with Play review materials. |
| §0.1, §3.7 offline/fail-safe behavior and honest VPN limits | Native policy/VPN runtime; health routes and child degraded states | Kotlin tests; child authenticated surface; health evidence | Partially implemented | Physical VPN conflict, captive portal, process-kill, and offline acceptance tests remain. |
| §0.1, §3.8 capability truth (`FULL`, `BEST_EFFORT`, `UNAVAILABLE`) | `capability/CapabilityDetector.kt`; parent health; child transparency | Native unit tests; authenticated health/child screenshots | Implemented | iOS capability values require an Apple build and device test. |
| §2.1 G1 universal app/category/network enforcement | `policy/PolicyManager.kt`, `GuardianPolicyRuntime.kt`, VPN, usage and inventory modules | Kotlin tests; live child policy/VPN evidence | Partially implemented | Android standard-mode bypass limits remain; physical-device coverage required. |
| §2.1 G2 guided setup without enterprise enrollment | Parent setup/pairing routes; child pairing route | Backend API tests; emulator pairing flows | Partially implemented | Full clean-install setup timing and physical-device acceptance remain. |
| §2.1 G3 local-first decisions | Native policy evaluator, reputation manager and VPN service | Reputation live evidence; Kotlin tests; `.scratch/emulator/reputation/` | Implemented | p95 performance target requires a representative physical-device run. |
| §2.1 G4 age-adaptive safety | `backend/app/policies/defaults.py`; signed policy schema; child copy | Backend policy tests; live younger-band reputation evidence | Implemented | Broader age-band product acceptance remains. |
| §2.1 G5 parent UX and three-interaction law | Parent routes and design system | Mobile tests; tablet artifacts; route inventory | Partially implemented | A complete manual §27 interaction audit on every listed surface remains. |
| §2.1 G6 transparent child UX | `apps/mobile/src/app/child/*`; block, time, permission and communication copy | Authenticated child screenshots; mobile tests | Implemented | Physical-device accessibility and age-band review remain. |
| §2.1 G7 privacy architecture | Native transient processing; minimized event schemas; deletion service | `.scratch/runtime-owasp/runtime-checks.txt`; account-deletion tests; Data Safety doc | Implemented | Independent privacy/store review remains. |
| §2.2 explicit non-goals: location, enterprise enrollment, TLS MITM, ads, covert monitoring | Android manifest, native modules and app dependencies | Release manifest and OWASP audit artifacts | Implemented | Recheck final release artifact before submission. |
| §2.3 product success metrics (setup, local p95, sync, battery, crash-free) | Instrumentation and backend timestamps in relevant modules | `.scratch/emulator/performance/` when complete; native metrics contract | Partially implemented | Battery, crash-free population, setup population and physical-device p95 require field/release measurement. |
| §4 age bands A–D and parent overrides | Policy defaults, policy mutations and signed policy bundle | `backend/tests/test_policy*.py`, policy live evidence | Implemented | Product review of every default/copy combination remains. |
| §4.2 canonical policy profile schema | `backend/app/policies/`; Android policy compiler/verifier | Backend policy and Kotlin unit tests | Implemented | iOS compiler/consumer is not present. |
| §4.4 child-visible policy | Child Home, My Time and permission/degraded surfaces | Authenticated child screenshots and mobile tests | Implemented | Physical-device acceptance remains. |
| §5 platform capability truth matrix | `CapabilityDetector.kt`, parent Health, child disclosure, iOS wording | Native tests; health screenshot; `Not available on iPhone/iPad` source/evidence | Partially implemented | Build and test iOS capability paths on macOS with entitlements. |
| §6.1 parent navigation: Home/Activity/Rules/Requests/Settings | `apps/mobile/src/app/parent/*` | Authenticated parent route screenshots; route inventory; mobile tests | Implemented | Complete authenticated accessibility traversal remains. |
| §6.2 child navigation: Home/My Time/Requests | `apps/mobile/src/app/child/*` | Authenticated child screenshots and mobile tests | Implemented | Block-surface and physical-device acceptance remain. |
| §6.3 tablet architecture and adaptive layouts | Shared responsive design system and Android tablet route rendering | `.scratch/emulator/tablet-parent-*.png` and XML artifacts | Partially implemented | iPad/iPadOS and native split-view require macOS simulator/device; Android tablet acceptance should be rerun after final UI changes. |
| §6.4 search/quick control | `apps/mobile/src/app/parent/quick-control.tsx` | Mobile tests/source inspection | Partially implemented | Complete three-interaction and discoverability audit remains. |
| §7 design system, typography, color, touch targets, motion and copy | `apps/mobile/src/design-system/index.tsx` and `src/design-system/tokens.ts` | Mobile lint/typecheck/tests; accessibility source audit | Partially implemented | Contrast and Dynamic Type need on-device measurement on all required routes. |
| §7.13 accessibility (labels, focus, contrast, large text, RTL, reduced motion) | Shared controls, labels, live regions, wrapping, opacity feedback | `.scratch/emulator/accessibility/`; authenticated screenshots captured in this run | Partially implemented | TalkBack traversal, contrast ratios, large-text clipping, RTL and reduced-motion need a complete route-by-route report; iOS Dynamic Type remains unverified. |
| FR-ACCOUNT-001 parent account and authentication | `backend/app/auth/`, mobile login/signup, session storage | Backend auth tests; authenticated parent emulator route | Implemented | Physical clean-install and account recovery acceptance remain. |
| FR-ACCOUNT-002 family creation and management | `backend/app/families/`, parent setup | Backend API tests; setup route | Implemented | Multi-parent physical acceptance remains. |
| FR-ACCOUNT-003 multiple guardians | FamilyGuardian model and guardian routes | Backend security/tenancy tests | Implemented | Push delivery and invite acceptance require provider/device testing. |
| FR-ACCOUNT-004 child profile and age band | Child routes/models and policy defaults | Backend API/policy tests | Implemented | Physical setup acceptance remains. |
| FR-ACCOUNT-005 device registration and pairing | Pairing routes, device credentials, child pairing screen | Backend pairing/security tests; emulator pairing evidence | Implemented | Physical-device pairing and key rotation remain. |
| FR-ACCOUNT-006 device-bound role | Role storage and pairing authorization | Mobile tests and route behavior | Partially implemented | Security review must validate reinstall/reset and same-account cross-device cases. |
| §8.2 parent onboarding and age preset | `parent/signup.tsx`, `parent/setup.tsx` | Mobile tests and emulator setup artifacts | Partially implemented | Full happy/error/offline flow and setup-time target remain. |
| §8.3 child pairing and guided Android permissions | `child/pair.tsx`, `parent/pairing.tsx`, Health disclosures | Backend security tests; authenticated emulator routes | Partially implemented | Physical permission denial/recovery acceptance required. |
| §8.4 parent Home | `parent/home.tsx` | Authenticated Home screenshot; mobile tests | Implemented | Route-level accessibility and populated-family evidence remain. |
| FR-APP-001–007 inventory, categories, controls, essential apps and new-app policy | `inventory/`, policy app rules, parent routes | Backend inventory/policy tests; native inventory tests | Partially implemented | iOS inventory/control path is absent; physical Android app-control acceptance remains. |
| FR-TIME-001–007 budgets, schedules, grants, warnings and expiry | Native usage/time evaluator; policy schema; child time surface; requests | Kotlin tests; backend policy tests; child My Time screenshot | Partially implemented | End-to-end real app expiry/overlay acceptance on physical Android and iOS is outstanding. |
| §8.7 routines and precedence | Policy compiler/evaluator and backend policy mutation service | Policy tests; live signed policy evidence | Implemented | Full routine matrix and physical boundary tests remain. |
| FR-WEB-001–008 category DB, decision layers, unknowns, parent rules, block UX, bypass and safe search | VPN service, policy runtime, reputation manager, child blocked-event surface | Live reputation evidence; Kotlin tests; foreground-service audit | Partially implemented | DNS/DoH/QUIC/IP-only, VPN conflict, captive portal and physical bypass tests remain; no TLS MITM is intentional. |
| §8.9 content intelligence taxonomy and verdicts | Backend reputation classifier/provider interfaces and signed bundles | `backend/tests/test_reputation.py`; `.scratch/emulator/reputation/` | Implemented | Production provider/feed integration and coverage are not verified. |
| §8.10 Android communication safety and privacy invariants | `GuardianNotificationListenerService.kt`, `CommunicationSafetyRuntime.kt`, detector, mobile surfaces | Native fixture test XML; runtime OWASP log audit; child/parent source and route evidence | Partially implemented | Physical notification/accessibility rendering, provider delivery and measured field accuracy remain. Rules detector is not a production ML model. |
| §8.10 iOS communication safety ceiling | iOS wording in shared UI/types | Source inspection and mobile tests | Partially implemented | Implement only permitted Screen Time/network metadata on macOS; verify entitlements and no notification listener claim. |
| §8.11 requests and approvals | Backend requests routers/models; parent/child request surfaces | Backend request tests; mobile tests | Implemented | End-to-end realtime approval on two physical devices remains. |
| §8.12 activity and reports, timezone/DST/multi-device | Usage aggregation service, report API, parent Activity | `backend/tests/test_usage_reports.py`; populated report artifact | Implemented | Populated authenticated rendering and physical multi-device report acceptance remain. |
| §8.13 protection Health and degradation | Health API, parent Health, child degraded states, capability detector | Backend health tests; authenticated Health screenshot | Implemented | Physical revocation/recovery and iOS health acceptance remain. |
| §8.14 tamper/circumvention handling | Native health events, permission recovery and policy state | OWASP/runtime audit; native tests | Partially implemented | Physical process-kill, VPN conflict and uninstall/reinstall scenarios remain. |
| §8.15 parent notifications, routing, quiet hours, dedupe/rate limits | `backend/app/notifications/`, PushSender, safety notification models | `backend/tests/test_safety_notifications.py`; persisted routing artifact | Implemented | APNs/FCM provider delivery cannot be verified without credentials and provider configuration. |
| §8.16 settings/privacy/appearance/help | Parent Home/Health/Rules and shared design system | Mobile tests; authenticated screenshots | Partially implemented | Complete screen inventory and platform settings acceptance remain. |
| §9 critical flows: pairing, limits, requests, block, disabled protection, high-risk signal | Parent/child routes, native policy/runtime, backend request/notification services | Focused backend/mobile/native tests; live reputation and child evidence | Partially implemented | Full two-device physical acceptance and all offline/error branches remain. |
| §10 Android architecture: VPN, UsageStats, inventory, notification listener, Accessibility, policy evaluator, storage and recovery | `apps/mobile/modules/guardian-protection/android/src/main/java/...` | Kotlin unit tests; release manifest; runtime OWASP audit; emulator routes | Partially implemented | Connected instrumentation and physical Android acceptance required; standard VPN limitations remain. |
| §11 iOS architecture, Family Controls, Managed Settings, Device Activity, Network Extension and extensions | `apps/mobile/plugins/withGuardianIOS` only; no complete Swift enforcement implementation | No Linux compilation evidence | Unimplemented | Implement native Swift targets, request Family Controls/Network Extension entitlements, build on macOS, and run iOS device/simulator tests. |
| §12 signed canonical policy, compilation, precedence and time evaluation | Backend signing/canonical JSON; Android verifier/compiler/evaluator | Backend and Kotlin tests; live signed policy evidence | Partially implemented | iOS verifier/compiler and cross-platform signature acceptance require Apple implementation/test. |
| §13 backend service boundaries, schema, pairing, device auth, realtime, push and rate limits | `backend/app/*`, Alembic migrations | Full backend tests; migration artifacts; OpenAPI generation | Partially implemented | Provider delivery and production deployment/scale tests remain. |
| §14 reputation distribution, delta chains, expiry and unknown classification | `backend/app/reputation/`, Android ReputationManager | Reputation tests and live pending→classify→delta evidence | Implemented | Real feed integration and production key rotation remain. |
| §15 on-device classification strategy and confidence | Rules-based deterministic detector; minimized event schema | Labelled fixture XML and runtime measurement | Partially implemented | No ML model is claimed; grow/measure independent production-labelled data before any model decision. |
| §16 parent/device APIs, idempotency and error model | FastAPI routers, generated OpenAPI/client, request-ID middleware | Backend pytest, OpenAPI drift check, request-ID tests | Implemented | Production contract and provider integration tests remain. |
| §17 shared RN architecture, offline UI, state and contracts | Expo Router, QueryClient, design system, contracts | Mobile typecheck/lint/Jest; authenticated routes | Implemented | iOS build and full offline visual acceptance remain. |
| §19 native bridge event contract | `GuardianProtectionModule.kt`, mobile contracts/client | Kotlin tests; `.scratch/emulator/correlation-webblocked-final.log`; `.scratch/backend-runtime.log` | Implemented | Physical-device and release-build correlation coverage remains. |
| §20 data classes, minimization, encryption, authorization, audit and deletion | Encrypted stores, backend auth/tenancy, account deletion service, Data Safety doc | Account deletion tests; runtime OWASP audit; request-ID tests | Implemented | Independent security/privacy review and physical storage inspection remain. |
| §21 performance/reliability budgets: hot path, cloud, battery, memory, network | `GuardianPerformanceMetrics.kt`, native instrumentation, backend timestamps | `.scratch/emulator/performance/nonzero-enforcement-logcat.txt`; `.scratch/emulator/performance/nonzero-enforcement-final.txt`; bundle measurement XML | Partially implemented | Representative p95 runs, battery historian/physical device remain; emulator exposes no usable package mAh. |
| §22 analytics/operational telemetry/privacy-conscious crash reporting | Request IDs, structured backend errors, health events and checkpoint observability audit | `.scratch/observability-review.md`; `.scratch/emulator/correlation-webblocked-final.log`; structured `http_request` lines in `.scratch/backend-runtime.log` | Implemented | Physical-device and production sink validation remain; no raw content may be added. |
| §23 Google Play and Apple Store requirements | Android manifest/disclosures/Data Safety; iOS plugin scaffolding | Play policy artifact, release manifest audit, Data Safety doc | Partially implemented | Submit Play declarations/reviewer credentials; obtain Apple entitlements and App Store review approval. |
| §24 phases and exit criteria | Commits/checkpoint and phase artifacts | `docs/DEVIN_CHECKPOINT.md`; test/evidence artifacts | Partially implemented | iOS and physical-device exit criteria are not met. |
| §26 screen inventory | Parent/child routes and tablet layouts | `.scratch/emulator/interaction-audit/README.md`; authenticated route screenshots in the same directory; tablet screenshots under `.scratch/emulator/tablet-*` | Partially implemented | The complete inventory is archived; several PRD destinations remain partial or missing as listed in the artifact. iPad/split-view requires Mac/Xcode. |
| §27 three-interaction compliance matrix | Parent route structure and direct Quick Control app/domain/bedtime surfaces | `.scratch/emulator/interaction-audit/README.md`; `parent-*.png`, `quick-control.png` | Partially implemented | 15 rows are recorded with tap counts or an explicit not-verified/gap status. Add-time, pause-internet, push approval, and child-only rows need populated fixtures or additional product operations. |
| §28 edge cases (multi-device, guardians, offline, timezone, reinstall, VPN/captive portal) | Backend tenancy/timezone logic; native health and policy runtime | `.scratch/emulator/interaction-audit/edge-case-probes.txt`; backend multi-device/timezone/guardian tests; connected tests | Partially implemented | Emulator probes verified process restart and the absence of a competing VPN package; timezone mutation was blocked by emulator property permissions, and captive portal, reinstall/re-pair, guardian #2 and multi-device live UI remain unverified. |
| §29 threat model T1–T9 | Native verification, signed bundles, auth/tenancy, privacy logging | `.scratch/owasp-mobile-code-review.md`, `.scratch/runtime-owasp/runtime-checks.txt` | Partially implemented | Independent penetration/Play review and physical tamper scenarios remain. |
| §30 unit, instrumentation, iOS, acceptance, network and accessibility testing | Backend tests, Jest, Kotlin tests, expanded connected flow test, emulator artifacts | `.scratch/emulator/interaction-audit/connected-test-count.txt`; connected XML reports; screenshots and route audit | Partially implemented | Two instrumented methods passed on three AVDs (6 executions); iOS tests and physical acceptance remain. |
| §31 UI states for every data surface | `DataState`, live regions, offline/stale/error/permission states | Mobile tests and source audit | Implemented | Route-by-route visual proof for every state remains. |
| §32 exact safety copy and iOS limitation | Parent/child copy and capability dialogs | Source search; authenticated child/health snapshots | Partially implemented | Verify exact copy in every locale and through Play review; iOS build remains unavailable. |
| §33 subscription/monetization architecture and no child-data advertising | No ad SDK or monetization path in app | Dependency/source audit | Partially implemented | Product/billing scope decision and store/legal review required before monetization. |
| §34 migration from YouTube prototype and security cleanup | Current Guardian app structure; no prototype dependency in core paths | Repository/source audit | Implemented | Final dead-code and prototype artifact search remains. |
| §35 engineering decisions ED-001–ED-011 | Architecture, native modules, policy and docs | Source and docs audit | Implemented | iOS decisions remain unverified until Apple build. |
| §36 technical spikes A–H | Android VPN/reputation work; iOS and classifier spikes documented | Existing research/audit artifacts | Partially implemented | Resolve iOS entitlement/filter spikes on macOS; resolve classifier spike with independent labelled data. |
| §37 product definition of done | Combined routes, services, tests and docs | This matrix and final sweep | Partially implemented | Physical devices, iOS, provider delivery, complete accessibility and release evidence remain. |
| §38 AC-APP-01/02, AC-TIME-01/02, AC-WEB-01/02/03, AC-REQ-01, AC-HEALTH-01/02, AC-PRIV-01, AC-IOS-CEILING-01, AC-UX-01 | Corresponding app/time/web/request/health/privacy routes and native/backend modules | Focused tests and emulator evidence listed above | Partially implemented | Run each acceptance criterion as a named end-to-end test; iOS criteria require macOS and entitlements. |

## Explicit external dependencies and remaining claims

The following are not claimed by this matrix:

1. **iOS compilation, entitlements, extensions, Family Controls, Managed
   Settings, Device Activity, Network Extension, or iOS physical behavior.**
   Build the committed iOS project on macOS, obtain Apple's Family Controls and
   Network Extension entitlements, and run simulator plus physical iPhone/iPad
   acceptance tests.
2. **APNs/FCM delivery.** Configure provider credentials and a test project,
   send sandbox/test notifications through the `PushSender` implementation,
   and record provider response, device receipt, quiet-hour, dedupe and
   retry evidence.
3. **Physical-device battery, performance, VPN, notification and Accessibility
   behavior.** Repeat the enforcement and accessibility sessions on supported
   Android phones and iOS devices; use battery historian or an equivalent
   vendor-supported energy measurement rather than inferring mAh from an
   emulator.
4. **Independent communication-safety accuracy.** The rules detector's labelled
   fixture measurement is not a production accuracy claim. Assemble an
   independently labelled, adversarial dataset, report per-category precision,
   recall, false-positive and false-negative counts, and only then decide
   whether a model is justified.
5. **Store approval and reviewer evidence.** Submit the Data Safety answers,
   Accessibility/notification/VPN/Usage Access declarations, prominent
   disclosures, account-deletion URL and reviewer credentials to Google Play;
   complete the equivalent Apple review package.
