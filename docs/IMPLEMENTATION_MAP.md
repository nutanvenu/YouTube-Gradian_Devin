# Guardian Implementation Map

Source of truth: `docs/Guardian_Master_PRD.md` (PRD). This map only records decisions and
sequencing; it is not a substitute for the PRD.

## Session/environment constraints (facts, not assumptions)

| Constraint | Impact |
|---|---|
| Build host is Linux (no macOS/Xcode) | iOS Swift sources, extension targets, entitlements, Info.plist and project wiring are authored and reviewed, but **cannot be compiled or run here**. iOS verification is an explicit external blocker (needs a Mac + physical device + Family Controls entitlement). |
| Family Controls / Network Extension entitlements require Apple approval | Code paths implemented and capability-gated; approval is an external action. |
| Android emulator available on host | Android is the platform we can compile, install and exercise end-to-end (VPN, UsageStats, Accessibility overlay, package events). |
| No production Supabase project provisioned | Backend runs against local Postgres (Docker) with Alembic migrations; Supabase-compatible SQL only. Managed-auth swap is behind an auth provider interface. |

## Architecture decisions (ADR-lite)

1. **Monorepo, pnpm workspaces.** `apps/mobile`, `backend`, `packages/{contracts,policy-schema,design-tokens,test-fixtures}` exactly as PRD §18.
2. **Contracts first.** `packages/contracts` holds the canonical TypeScript domain types; the canonical
   policy bundle is defined once as JSON Schema in `packages/policy-schema` and is the single artifact
   the backend (Python), Kotlin and Swift engines all validate against. Kotlin/Swift models are
   hand-written to that schema, with schema-driven conformance fixtures in `packages/test-fixtures`
   shared by all three test suites. Rationale: three languages cannot share generated code cheaply,
   but they can share *fixtures*, and fixtures are what actually catch precedence drift.
3. **One policy semantics, three implementations, one conformance suite.** The precedence ladder
   (PRD §12.3) and time semantics (§12.4) are encoded as declarative fixture cases
   (`policy-decision-cases.json`): context in, expected `{action, reason_code}` out. TS reference
   evaluator, Kotlin evaluator and Swift evaluator all run the same cases. A new rule type is not
   "done" until it has cases and all three suites pass.
4. **Signed bundles.** Ed25519 (PRD §12.1). Backend holds the private key (env/KMS), devices hold the
   public key pinned at build time + rotation slot in the bundle header. Bundle apply is atomic:
   verify → validate → compile → swap → ack (§12.2). Previous snapshot retained for rollback.
5. **Native hot path only.** JS never sees packets/usage events; bridge exposes the coarse API of
   PRD §10.3 and the semantic event union of §19.
6. **Capability model is first-class.** `Capability` = `FULL | BEST_EFFORT | UNAVAILABLE | REGION_LIMITED`
   (§3.8) is reported by native, stored on `devices.capabilities_json`, and drives UI copy. No screen
   renders a value it cannot know: `unknown` is a distinct state from `0` (§31).
7. **Modular monolith backend**, FastAPI + SQLAlchemy + Alembic, module boundaries per §13.3.
   Device auth is a separate revocable credential from parent JWT (§13.6).
8. **Fail-safe, not fail-open, and never brick.** Blocked-known stays blocked offline; allowed-known
   stays allowed unless a schedule overrides; unknown follows the age-band unknown policy (§3.7).

## Phase 1 slices (each slice = contracts + backend + native + UI + tests + runtime proof)

| # | Slice | Verification gate |
|---|---|---|
| 1.0 | Toolchain + monorepo skeleton + CI (lint/typecheck/test) | CI green locally |
| 1.1 | Contracts + policy schema + TS reference evaluator + conformance fixtures | fixture suite green |
| 1.2 | Backend: auth, family, children, guardians; migrations | pytest + httpx API tests |
| 1.3 | Backend: pairing (QR + 6-digit, TTL, single-use, rate limit), device registration/keypair, device auth, heartbeat | pytest incl. abuse cases |
| 1.4 | Backend: policy documents/versions → signed bundle issue/apply-ack; requests service; event ingestion; health; WS realtime | pytest incl. signature tamper + idempotency |
| 1.5 | Mobile shell: Expo dev-client app, design tokens/components, role selection, parent auth, family/child creation, age presets, pairing QR | jest + emulator run |
| 1.6 | Android native: GuardianProtection Expo module, LocalPolicyStore + compiled snapshot + evaluator (Kotlin conformance suite), permission/health plumbing | unit + instrumented on emulator |
| 1.7 | Android native: VpnService TUN + DNS inspection + domain policy + flow attribution + block events | instrumented: DNS block observed on emulator |
| 1.8 | Android native: UsageStats measurement, LauncherApps inventory, package-change monitoring, daily/app limits, routines, Accessibility foreground observer + block overlay | instrumented + emulator UI proof |
| 1.9 | Parent/child product surfaces: Parent Home, Rules, Requests, Activity skeleton, Protection Health, Child Home/My Time/Requests, Quick Control, tablet two-pane | emulator flows incl. offline/stale/permission-denied states |
| 1.10 | iOS: Swift managers (FamilyControls auth, ManagedSettings reconciliation, DeviceActivity monitors, filter data/control providers) + extension targets/entitlements + Xcode project wiring | authored + reviewed; compile/device verification blocked on macOS |

Phase 2 and Phase 3 follow PRD §24 and are not re-planned here until Phase 1 exit criteria (§24 Phase 1)
are met on a real Android device/emulator.
