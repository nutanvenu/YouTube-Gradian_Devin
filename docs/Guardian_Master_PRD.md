# Guardian - Master Product Requirements Document

**Status:** Build-ready master PRD  
**Working product name:** Guardian  
**Platforms:** Android phones/tablets; iPhone/iPad  
**Mobile architecture:** React Native + Expo Development Builds + native Kotlin/Swift enforcement engines  
**Backend:** FastAPI + PostgreSQL/Supabase-compatible architecture  
**Primary build objective:** Build fast, ship quickly, minimize ceremony, preserve correctness and privacy  
**Target users:** Families with children ages 5-17  
**Product scope:** Digital safety, app controls, screen time, web/content protection, risk signals, parent approvals  
**Explicitly out of scope:** Location tracking, geofencing, enterprise device management, device-owner/supervised enterprise setup, TLS interception

---

## 0. Build Directive for Codex and Engineering Agents

This document is the implementation authority for Guardian. Engineering agents should treat it as a product specification, architecture specification, interaction specification, and definition-of-done document.

### 0.1 Execution rules

1. Build the product in the three phases defined in this PRD. Do not invent a fourth product phase.
2. Prefer working vertical slices over framework-heavy abstraction.
3. Do not use Expo Go. Use Expo Development Builds and committed native Android/iOS projects.
4. Keep all enforcement-critical and latency-critical logic native:
   - Android: Kotlin.
   - iOS/iPadOS: Swift and Apple app extensions.
5. Keep UI, navigation, account flows, family management, configuration, API clients, and non-hot-path business logic shared in React Native/TypeScript where practical.
6. Never send individual network packets, usage events, or screen events through the JS bridge for real-time policy decisions.
7. Enforce policy locally first. Cloud intelligence is an augmentation layer, not a dependency for normal allow/block decisions.
8. Every network, app, and time policy must continue to function with the cloud unavailable using the most recent valid signed policy bundle.
9. No TLS man-in-the-middle interception, root certificate installation, certificate pinning bypass, or traffic decryption of third-party apps.
10. No raw child message body, notification body, screenshot, browsing payload, or network payload may leave the child device by default.
11. Do not claim cross-platform capabilities that the OS does not provide. Platform degradation must be explicit and graceful.
12. The parent-facing UX must make all normal user-facing capabilities reachable within three deliberate interactions from the Home surface. This is the Guardian 3-Interaction Law, not an Apple-published rule.
13. Emergency and frequent actions should require fewer interactions:
    - 1 interaction: Pause protection-dependent access, respond to urgent request from notification, protection-health remediation when possible.
    - <=2 interactions: Add time, block an app from a child summary, approve/deny a request.
    - <=3 interactions: Every other normal feature.
14. Use system-native interaction behavior on each platform even when the visual language is shared.
15. Do not hide monitoring from the child. Guardian is a transparent parental-safety product, not covert surveillance software.
16. No advertising SDKs, behavioral advertising, data sale, or monetization based on child activity data.
17. Any feature marked **Platform Ceiling** must not be faked with misleading UI or analytics.
18. Each phase ends with compiling Android and iOS builds, automated tests for that phase, and on-device smoke tests.

### 0.2 Definition of build-ready

A feature is not complete merely because a screen exists. A feature is complete only when:

- The UI exists in parent and/or child role as specified.
- The native/platform implementation works on physical devices.
- Permissions and denial states are handled.
- Offline behavior is defined and implemented.
- Policy changes propagate and are versioned.
- Relevant activity is auditable without storing unnecessary raw child content.
- Edge cases and failure states are handled.
- Accessibility labels and touch targets are present.
- Android and iOS differences are represented honestly.
- Automated tests cover deterministic logic.
- A physical-device acceptance test passes.

---

# 1. Executive Summary

Guardian is a consumer parental-control and digital-safety platform for families with children ages 5-17. Guardian must control digital behavior at the operating-system and network-policy boundaries rather than depending on integrations with individual consumer apps.

The product must answer four parent questions continuously:

1. **What can my child use?** - app and category controls.
2. **When and for how long can they use it?** - screen-time budgets, schedules, routines, temporary extensions.
3. **What can the device reach?** - web/domain/network filtering and content categories.
4. **Is something risky happening?** - local risk signals from network activity, app usage, and, where the operating system permits, notification or visible UI text.

Guardian's core thesis is:

> Protect the device universally at the OS boundary, enrich decisions using content intelligence when the OS exposes useful signals, and avoid per-app integrations as a dependency.

Guardian should not feel like cybersecurity software. It should feel like a calm family system utility: understandable in seconds, trustworthy, visually quiet, and decisive when something needs attention.

### 1.1 Product promise

Guardian provides:

- App discovery and app/category controls.
- Daily and per-app time limits.
- Schedules, bedtime, school/focus routines, and temporary allowances.
- Network/domain content filtering across browsers and apps.
- Category-based web protection.
- Unknown domain and new app evaluation.
- Parent approval requests.
- Protection health and tamper/degraded-state alerts.
- Age-adaptive defaults and explanations.
- Android notification-based risk detection when the parent enables it.
- Android visible-screen risk signals through an optional, explicitly disclosed Accessibility capability when enabled.
- iOS Screen Time enforcement through Family Controls, Managed Settings, and Device Activity.
- iOS network filtering through Network Extension content filtering on authorized child devices.

### 1.2 What Guardian must never promise

Guardian must never claim that it can read every message, inspect every video frame, or understand every encrypted interaction in every third-party app.

Modern apps use encrypted network transport and OS sandboxes. A device-wide network filter can often identify a source app, destination, domain, timing, and traffic metadata; it cannot generically read the encrypted message or media payload.

On Android, Guardian can gain additional user-authorized signals through notification access and Accessibility. These remain best-effort because apps may hide notification previews, render content in inaccessible custom views, or restrict capture.

On iOS, there is no public API that allows Guardian to read arbitrary third-party app notifications or messages. Guardian must instead use Screen Time controls, source-app network-flow metadata, domain/URL filtering where Apple exposes it, and usage risk signals. This is a hard platform ceiling.

---

# 2. Product Goals, Non-Goals, and Success Criteria

## 2.1 Primary goals

### G1. Universal enforcement without per-app integrations

A newly released browser, game, social app, or chat app must still fall under Guardian's baseline controls because Guardian enforces at app-usage, network, schedule, and OS-control layers.

### G2. Fast setup

The product is consumer software, not enterprise MDM. A parent should be able to establish meaningful protection on a child's device through a guided install and permission flow without factory reset, device-owner provisioning, supervised enterprise enrollment, or technical networking knowledge.

### G3. Local-first enforcement

Routine allow/block decisions should execute on-device in milliseconds. Internet outages must not disable normal restrictions.

### G4. Age-adaptive safety

A five-year-old and a seventeen-year-old must not receive the same controls, language, block explanations, activity visibility, or autonomy assumptions.

### G5. Low-friction parent UX

Guardian must surface the most frequent actions immediately and make the entire product navigable within the Guardian 3-Interaction Law.

### G6. Transparent child UX

The child must understand when a rule exists, why something is blocked, how much time remains, and how to ask a parent. The product must avoid shame, fear, or punitive language.

### G7. Privacy as architecture

Guardian should know enough to protect, but collect less than competitors whenever possible. Raw child content is processed locally by default and discarded unless a parent explicitly requests a report flow that requires otherwise.

### G8. Fast engineering execution

The implementation must use a shared React Native UI and targeted native engines rather than duplicating whole products in Kotlin and Swift.

## 2.2 Non-goals

The first production product does not include:

- Live location.
- Location history.
- Geofencing.
- SOS/location sharing.
- Phone call recording.
- SMS database extraction.
- Social platform account credentials.
- App-specific private API integrations.
- Root/jailbreak-based interception.
- Android Device Owner or enterprise DPC enrollment.
- Apple supervised-device/MDM deployment.
- TLS interception.
- Full packet tunneling through Guardian servers as a default architecture.
- Advertising.
- Covert/stalkerware operation.

## 2.3 Product-level success metrics

These are product targets, not guaranteed values before measurement.

- >=90% of parents complete core setup without support.
- Median standard setup: <=7 minutes after account creation, excluding Apple Family Sharing issues.
- >=95% of local policy decisions occur without cloud round-trip.
- Cached domain decision p95: <=10 ms inside native filtering engine.
- Parent policy update to online child device p95: <=5 seconds.
- Parent approval event to online child device p95: <=3 seconds.
- Protection health freshness: <=5 minutes when device is online.
- No normal app navigation path exceeds 3 deliberate interactions from Home.
- Crash-free sessions target >=99.7% after launch stabilization.
- Battery overhead from Guardian target: <5% of daily battery in ordinary use; stretch target <3%.
- Raw child private-content retention by default: 0 seconds after local classification, except ephemeral in-memory processing.

---

# 3. Hard Product Invariants

These are non-negotiable unless the PRD is deliberately revised.

## 3.1 Guardian 3-Interaction Law

Every normal user-facing capability has a path from Home requiring no more than three deliberate taps/clicks. Search/command is a valid route.

**Onboarding and operating-system permission flows are exempt** because Apple/Google system sheets may require more interactions outside Guardian's UI.

## 3.2 One-app role model

Ship one mobile binary/product brand. On first launch, the user chooses or is invited into a role:

- Parent/Guardian device.
- Child device.

The same account may have parent role on one device and child role on another only through family assignment; a child device must not expose parent controls simply because the same app binary contains them.

Role is persisted per device and cryptographically bound to the paired family/device registration.

## 3.3 No location

Do not add location permissions, maps, geofences, or passive location telemetry.

## 3.4 No enterprise enrollment

Do not require Android Device Owner, work profile, MDM, Apple supervision, or factory reset.

## 3.5 Local-first child privacy

- Raw notification text: local-only by default.
- Raw Accessibility tree/text: local-only by default.
- Raw packet payload: never uploaded by default.
- Screenshots: do not capture continuously and do not upload by default.
- Message text: do not persist unless an explicit future parental report feature is separately reviewed and enabled.
- Domain and app metadata may be synchronized only when required for parent controls/reporting and must be minimized.

## 3.6 No TLS interception

Guardian must not install a custom root CA or decrypt third-party TLS sessions.

## 3.7 Fail safely, but do not brick connectivity

- Local known blocks remain blocked offline.
- Local known allows remain allowed offline unless an active schedule overrides them.
- Unknown destinations follow the age-band unknown-content policy.
- Standard Android mode cannot force VPN lockdown without user/system configuration; Guardian must never pretend otherwise.
- If the filter crashes, the app should restart its local service when the OS permits and immediately surface degraded protection to the parent.

## 3.8 Platform honesty

Capabilities must be tagged internally as:

- `FULL` - supported by public platform APIs with reliable semantics.
- `BEST_EFFORT` - possible but subject to app rendering, OS restrictions, permission state, or race conditions.
- `UNAVAILABLE` - no supported public capability.
- `REGION_LIMITED` - available only under regional entitlement/authorization rules.

---

# 4. User Model and Age-Adaptive Policy System

## 4.1 Age bands

Guardian uses four policy bands. Parents can override individual rules, but the default policy posture is derived from age.

### Band A - Young Child: 5-8

**Product posture:** Strong guidance and allow-oriented safety.

Default behaviors:

- Strong adult/sexual/gambling/self-harm/drug/hate/graphic-violence blocking.
- Unknown high-risk websites: block pending classification.
- Unknown apps: notify parent and place into limited mode until reviewed when technically enforceable.
- Social/anonymous chat categories: blocked by default.
- Shorter daily entertainment limits.
- Bedtime schedule enabled by onboarding recommendation.
- Search/content strictness high.
- Child explanations use simple language and concrete next step.
- Parent sees more proactive alerts.
- Requests are simple: `Ask for this`, `Ask for 15 more minutes`.

Example child copy:

> This site is not available because it may show grown-up content. You can ask your parent if you think it should be allowed.

### Band B - Preteen: 9-12

**Product posture:** Guided independence.

Default behaviors:

- Same hard-risk categories strongly blocked.
- Social and chat apps require parent decision or time limits by default.
- Unknown websites may be briefly evaluated before decision; high-risk unknowns remain blocked.
- More granular app/category time budgets.
- Parent alerts focus on repeated or high-confidence events instead of every minor block.
- Child gets remaining-time indicators and clearer reasons.

### Band C - Teen: 13-15

**Product posture:** Guardrails plus transparency.

Default behaviors:

- Hard-risk web categories remain protected.
- Social apps are not universally blocked; schedules and budgets are emphasized.
- Parent receives high-severity safety events and meaningful trends, not exhaustive surveillance.
- Unknown websites default to allow when reputation is neutral, unless parent selects strict web mode.
- Child can see their own weekly usage and proactively request schedule changes.
- Block explanations avoid infantilizing language.

### Band D - Older Teen: 16-17

**Product posture:** Safety net plus self-management.

Default behaviors:

- Hard-risk categories remain available for parent policy.
- Default emphasis shifts toward downtime, focus, unsafe-site protection, and high-severity risk alerts.
- Lower-severity social/message signals are summarized rather than pushed immediately.
- Child gets full personal time dashboard and clear view of active family rules.
- Parents are encouraged toward conversation and temporary controls rather than blanket blocking.

## 4.2 Policy profile schema

```json
{
  "profile_id": "child_123",
  "age": 11,
  "age_band": "PRETEEN",
  "timezone": "Asia/Kolkata",
  "content_mode": "AGE_DEFAULT",
  "unknown_domain_policy": "BLOCK_WHILE_CLASSIFYING",
  "unknown_app_policy": "LIMIT_AND_NOTIFY",
  "daily_device_budget_minutes": 180,
  "category_budgets": {},
  "app_overrides": {},
  "web_categories": {},
  "routines": [],
  "communication_safety": {
    "enabled": true,
    "severity_threshold": "HIGH",
    "android_notification_signals": true,
    "android_accessibility_signals": false
  },
  "parent_custom_intent": null,
  "version": 1
}
```

## 4.3 Parent overrides

Parents can override defaults at any granularity:

- Allow/block app.
- Unlimited app.
- App-specific daily time.
- App schedule.
- App category budget.
- Domain allow/block.
- Web category allow/block.
- Unknown-content strictness.
- Routine rules.
- Temporary exception.
- Communication-safety sensitivity.

Every override records:

- Author parent ID.
- Timestamp.
- Effective time.
- Expiry if temporary.
- Original default.
- New value.
- Policy version.

## 4.4 Child-visible policy

The child must be able to see a simple, non-technical summary of active rules:

- Bedtime.
- Time left today.
- Apps with limits.
- Apps/sites blocked.
- Whether web protection is active.
- How to request changes.

The child does not need access to parent-only risk evidence or internal classifier scores.

---

# 5. Platform Capability Truth Matrix

This matrix is authoritative. Product copy and UI must match it.

| Capability | Android standard install | iPhone/iPad standard install |
|---|---|---|
| App/category time limits | FULL with Usage Access + enforcement service; app-blocking mechanics require Accessibility for strongest standard-mode UX | FULL through Device Activity + Managed Settings for authorized child devices |
| Hard OS app shield | BEST_EFFORT without Device Owner; use Accessibility block overlay/back-home plus network denial | FULL through Managed Settings shields |
| Installed/launchable app discovery | FULL for launchable apps via LauncherApps; broader package inventory must respect Play package-visibility policy | Tokenized app/category selection is FULL; non-tokenized installed app data is REGION_LIMITED to eligible EU authorization |
| New app detection | FULL via package change signals/observed launchable apps | BEST_EFFORT through Screen Time selection/data surfaces; actual inventory outside EU remains privacy-preserving/tokenized |
| Foreground usage events | FULL with Usage Access | FULL for configured Screen Time monitoring, privacy-preserving |
| Device-wide network filtering | FULL with VpnService after user consent | FULL on authorized child devices through Network Extension content filters |
| Source app for network flow | FULL where Android connection ownership APIs can resolve active flow UID; otherwise correlate UID/socket/DNS metadata | FULL when NEFilterFlow exposes sourceAppIdentifier/source metadata |
| Domain blocking | FULL | FULL |
| Full URL filtering | LIMITED/BEST_EFFORT generically; do not MITM HTTPS | Enhanced on iOS 26+ for WebKit/URLSession via Network Extension URL Filter; otherwise content/browser flow capability varies |
| Third-party notification text | FULL after explicit Notification Access, subject to notification preview contents | UNAVAILABLE for arbitrary third-party apps |
| Third-party visible UI text | BEST_EFFORT through Accessibility when explicitly enabled; some apps/custom views expose little or nothing | UNAVAILABLE as a general public cross-app inspection API |
| Read arbitrary private messages | UNAVAILABLE as a guarantee; only signals exposed through notification/UI accessibility can be evaluated | UNAVAILABLE |
| Inspect encrypted HTTPS message/media payload | UNAVAILABLE without prohibited MITM; Guardian does not MITM | UNAVAILABLE; Guardian does not MITM |
| Prevent child uninstalling Guardian | BEST_EFFORT only in standard mode; detect and discourage tampering, no enterprise guarantee | FULL after Family Controls child authorization: Apple prevents child deletion while authorized |
| Force always-on VPN without enterprise ownership | User can choose Android always-on VPN in Settings; Guardian cannot force it as normal app | Network filter is managed through Family Controls/Network Extension authorization path |
| Offline enforcement | FULL for cached/local rules while services remain enabled | FULL for local Screen Time/Managed Settings/network filter rules |
| Parent remote policy | FULL through Guardian cloud sync | FULL for Guardian-owned policy; Apple Screen Time data remains subject to privacy rules |
| Parent remote per-app activity details | FULL from Guardian-collected minimized usage metadata, with disclosure | LIMITED by Apple's privacy sandbox outside specific APIs/regions; do not promise arbitrary export of per-app Screen Time data |

## 5.1 Platform ceiling: social and messaging safety

The product requirement is universal risk detection where the operating system exposes signals, not universal message interception.

### Android signal sources

1. NotificationListenerService - local analysis of posted notification title/text when present.
2. AccessibilityService - optional local analysis of visible UI text exposed in the accessibility tree.
3. Source-app network metadata - destination risk and behavioral signals.
4. Usage metadata - app/category/time patterns.
5. Links/domains opened - domain/category reputation.

### iOS signal sources

1. App/category usage through Screen Time frameworks.
2. NetworkExtension flow source app + destination/URL metadata where available.
3. Web/domain risk.
4. Parent-defined app/category restrictions.
5. No arbitrary third-party notification or message-body inspection.

The UI must call the iOS feature **Communication Risk Signals**, not **Message Monitoring**, unless a future supported Apple API genuinely provides it.

---

# 6. Product Information Architecture

## 6.1 Parent role navigation

Phone primary navigation uses five destinations maximum:

1. **Home**
2. **Activity**
3. **Rules**
4. **Requests**
5. **Settings**

A persistent toolbar action provides **Guardian Search / Quick Control**.

### Home

Purpose: Answer "Are my children protected, and is anything needing attention?"

Contents:

- Family protection health.
- Child cards.
- Pending requests.
- Urgent safety alerts.
- Today summary.
- Quick controls.

### Activity

Purpose: Understand usage and protection outcomes without drowning in logs.

Contents:

- Child selector.
- Screen time.
- App/category breakdown where platform permits.
- Web protection summary.
- Safety events.
- Trends.

### Rules

Purpose: Configure all policy.

Contents:

- Child selector.
- Apps.
- Screen Time.
- Routines.
- Web & Content.
- Communication Safety.
- Custom allow/block rules.

### Requests

Purpose: One inbox for child approvals.

Contents:

- Pending.
- Recently resolved.
- Request filters.
- One-tap approve/deny actions.

### Settings

Purpose: Family/account/device configuration, privacy, protection health, notifications, security, help.

## 6.2 Child role navigation

Use three destinations:

1. **Home**
2. **My Time**
3. **Requests**

The child Home must make current status understandable in less than five seconds.

### Child Home

- Protection active state.
- Time remaining.
- Current routine/mode.
- Next scheduled change.
- `Ask Parent` primary action.
- Any current block explanation.

### My Time

- Today usage.
- Category usage.
- Limits.
- Week trend appropriate for age.

### Requests

- New request.
- Pending requests.
- Parent decisions.

## 6.3 Tablet architecture

Do not stretch phone UI.

### iPad

Use Apple-native split-view behavior:

- Sidebar: Home, Activity, Rules, Requests, Settings.
- Optional child list in sidebar/secondary column.
- Detail content in primary pane.
- Inspector-style configuration where appropriate.

### Android tablet

Use adaptive two-pane layout:

- Navigation rail/sidebar.
- Master list left.
- Detail right.
- Maintain identical semantic hierarchy to iPad, but Android-native back/navigation behavior.

## 6.4 Guardian Search / Quick Control

Accessible from Home in one interaction and from every primary screen.

Search across:

- Children.
- Apps.
- Rules.
- Web categories.
- Routines.
- Settings.
- Requests.
- Help.

Action examples:

- `Pause internet for Emma`
- `Give Arjun 15 minutes`
- `Block Instagram`
- `Bedtime at 9:30 PM`
- `Allow YouTube until 7 PM`
- `Show blocked websites today`
- `Turn on strict web protection`

For V1, this is deterministic command/search, not a cloud LLM dependency. Natural-language interpretation may use a constrained local/parser or backend only after explicit confirmation.

---

# 7. Guardian Design System

## 7.1 Design authority

The primary reference is Apple's current Human Interface Guidelines. Guardian adopts the principles and platform conventions rather than reproducing Apple's copyrighted documentation or pretending non-Apple UI is a first-party Apple interface.

Guardian's design principles are derived from Apple's current HIG principles:

1. **Purpose** - every surface exists to help a family understand or act.
2. **Agency** - parent and child understand what is happening and can take the next appropriate action.
3. **Flexibility** - adaptive age bands, phones/tablets, accessibility settings, and different family routines.
4. **Simplicity** - remove unnecessary controls, prioritize frequent actions, keep navigation obvious.
5. **Craft** - precise alignment, spacing, animation, states, copy, and native behavior.
6. **Delight** - calm reassurance, subtle motion, high-quality haptics, and compassionate child-facing language.

## 7.2 Emotional design target

Guardian should feel:

- Calm.
- Safe.
- Premium.
- Familiar.
- Lightweight.
- Trustworthy.
- Respectful.

Guardian should not feel:

- Militaristic.
- Alarmist.
- Hacker-themed.
- Surveillance-heavy.
- Punitive.
- Enterprise-admin-like.
- Data-dense by default.

## 7.3 Visual hierarchy

Every screen follows:

1. Current state.
2. Most likely next action.
3. Explanation/context.
4. Secondary details.
5. Advanced configuration.

Do not make cards compete equally for attention.

Use whitespace as the primary grouping mechanism before borders.

## 7.4 Materials and surfaces

### iOS/iPadOS

On current Apple OS versions, use system-provided materials and Liquid Glass behavior for navigation/control layers where the OS supplies it.

Use glass/materials primarily for:

- Navigation bars.
- Tab bars.
- Toolbars.
- Floating quick-control surfaces.
- Compact transient control groups.

Do not turn every content card into glass. Primary content should remain stable, readable, and calm.

Older supported iOS versions fall back to native system materials automatically/conditionally.

### Android

Use edge-to-edge layouts and Android-native insets/navigation behavior. Preserve Guardian's spacing, typography hierarchy, semantic colors, and surface hierarchy without recreating Apple system chrome literally.

## 7.5 Typography

### iOS/iPadOS

Use the Apple system font through semantic system text styles. Do not bundle or distribute Apple font files.

Use Dynamic Type everywhere.

Preferred semantic styles:

- Large Title - top-level page titles when appropriate.
- Title 1/2/3 - section hierarchy.
- Headline - high-emphasis compact labels.
- Body - default descriptive copy.
- Callout - compact detail.
- Subheadline - secondary labels.
- Footnote/Caption - metadata only.

Base body should align with Apple's default 17 pt behavior and scale with accessibility sizes.

### Android

Use **Inter Variable** as Guardian's primary custom UI typeface unless user testing shows the Android system font provides better native cohesion. Atlassian Sans is derived from Inter Variable; Guardian borrows Atlassian's readability and information-density thesis, not Atlassian's proprietary brand font.

Typography principles inspired by Atlassian Design:

- Optimize for readability first.
- Strong differentiation of letterforms.
- Compact, controlled heading hierarchy.
- Consistent line height.
- Avoid excessive font-size variety.
- Use tabular numerals for time/usage metrics.
- Use semibold rather than ultra-bold for most hierarchy.
- Never use thin weights for essential information.

### Shared semantic type tokens

```text
text.largeTitle
text.title1
text.title2
text.title3
text.headline
text.body
text.callout
text.subheadline
text.footnote
text.caption
text.metricLarge
text.metricMedium
```

React Native components map semantic tokens to platform-native values.

## 7.6 Color

Use semantic color tokens, not hard-coded colors throughout components.

```text
color.background
color.backgroundElevated
color.surface
color.surfaceSecondary
color.textPrimary
color.textSecondary
color.textTertiary
color.separator
color.accent
color.success
color.warning
color.danger
color.info
color.blocked
color.allowed
color.pending
```

Rules:

- Support light and dark appearance.
- Use system semantic colors on iOS where possible.
- Red is reserved for destructive actions and genuine danger/high-risk safety events.
- Ordinary blocked content should often use neutral/warning treatment, not emergency red.
- Green indicates healthy protection/allowed state, not gamified achievement.
- Never communicate status by color alone.

## 7.7 Iconography

### iOS

Use SF Symbols through system APIs when licensing/semantic use permits.

### Android

Use a Guardian semantic icon mapping to Material Symbols or Guardian-owned vector assets.

Do not export Apple trademark/product symbols into Android assets.

Shared semantic icon names:

```text
guardian.shield
guardian.child
guardian.apps
guardian.web
guardian.time
guardian.routine
guardian.request
guardian.activity
guardian.warning
guardian.block
guardian.allow
guardian.pause
guardian.search
guardian.settings
guardian.communication
guardian.health
```

## 7.8 Touch targets

- iOS/iPadOS: normal interactive target minimum 44 x 44 pt.
- Android: minimum 48 x 48 dp.
- Compact visual icons can be smaller only when hit area remains compliant.
- Provide sufficient spacing between adjacent controls.

## 7.9 Navigation rules

- Use platform-native back behavior.
- iOS: navigation stack, sheets, popovers, tab/sidebar conventions.
- Android: predictive back compatible navigation, bottom nav/rail as appropriate.
- Never invent a custom back gesture.
- Do not put critical navigation behind a hamburger menu on phone.
- Do not exceed five primary destinations.

## 7.10 Sheets, dialogs, and alerts

Use a sheet for:

- Editing one policy.
- Quick controls.
- Temporary time grant.
- Selecting a routine.
- Choosing a child.

Use an alert only for:

- Critical confirmation.
- Destructive irreversible actions.
- Protection failure requiring immediate understanding.

Use inline validation for normal errors.

## 7.11 Motion

Motion must communicate state change, hierarchy, and continuity.

Rules:

- Respect Reduce Motion.
- No decorative continuous animation on protection status.
- Use subtle matched transition for child card -> child detail.
- Block/allow states transition quickly, not theatrically.
- A parent's approval should feel immediate on the child's device.
- Skeletons are preferred over indefinite spinners for content loading.

## 7.12 Haptics

Use native haptics sparingly:

- Light selection haptic for mode/routine selection.
- Success haptic for parent approval or protection repair.
- Warning haptic for disabling protection.
- Destructive haptic for delete/unpair confirmation.

Do not vibrate on every blocked web request.

## 7.13 Accessibility

Required:

- VoiceOver and TalkBack labels for all interactive controls.
- Logical focus order.
- Dynamic Type / scalable text.
- 200% text-size resilience target where platform supports.
- Bold Text compatibility.
- Increased Contrast compatibility.
- Reduce Motion.
- Reduce Transparency.
- No color-only status.
- Screen-reader descriptions for charts.
- RTL mirroring.
- Keyboard navigation on tablets where supported.
- Switch Control compatibility on iOS.
- Minimum touch target compliance.

## 7.14 Copy system

Parent copy is concise and action-oriented.

Good:

> Web protection is off on Emma's phone. Turn it back on to restore blocking.

Bad:

> Critical network security subsystem failure detected.

Child copy is age-adaptive and never accusatory.

Good:

> Your game time is finished for today. You can ask for 15 more minutes.

Bad:

> ACCESS VIOLATION. APPLICATION BLOCKED.

---
# 8. Feature Requirements

## 8.1 Accounts, Families, Roles, and Devices

### FR-ACCOUNT-001 - Parent account

Parent can create an account with:

- Email + password.
- Apple sign-in on iOS where appropriate.
- Google sign-in where appropriate.

MVP can launch with email/password plus magic-link/password reset if speed requires. Authentication choice must not delay core parental-control engineering.

### FR-ACCOUNT-002 - Family

A parent account owns or belongs to a `family`.

Family fields:

```text
id
name
created_at
owner_parent_id
subscription_state
policy_defaults_version
```

### FR-ACCOUNT-003 - Multiple parents/guardians

Support at least two guardians per family.

Roles:

- Owner guardian.
- Guardian.

Both can approve child requests unless owner disables approval permission for another guardian in a future release.

### FR-ACCOUNT-004 - Child profile

Required fields:

- Display name.
- Date of birth or age.
- Derived age band.
- Optional avatar color/icon.
- Time zone inherited from device/family, editable by parent.

Do not require child email.

### FR-ACCOUNT-005 - Device registration

Each physical child device has:

```text
device_id
family_id
child_profile_id
platform
platform_version
app_version
device_model_display
role
public_key
protection_state
last_seen_at
policy_version_applied
capabilities
```

Do not store hardware identifiers such as IMEI for identity.

### FR-ACCOUNT-006 - One app, device-bound role

Initial route:

```text
Welcome to Guardian

[I'm a parent or guardian]
[This is a child's device]
```

If launched from a child pairing deep link/QR, preselect Child role.

Once paired as a child device, changing role requires parent authorization and unpairing.

---

## 8.2 Parent Onboarding

### Product goal

Get from install to meaningful protection with minimal cognitive load.

### Parent onboarding sequence

1. Welcome.
2. Sign in/create account.
3. Create or join family.
4. `Add a child`.
5. Child name + age.
6. Recommended protection preset based on age.
7. Pair child device QR/code.
8. Parent Home shows child setup progress in real time.

### Recommended age preset screen

Example:

```text
Recommended for age 10

Web safety             Strong
Social & chat          Ask first
Entertainment          2 h/day
Bedtime                9:00 PM - 6:30 AM
Unknown websites       Check before opening

[Use recommended]
[Customize]
```

Use recommended defaults as the primary action.

---

## 8.3 Child Device Pairing and Protection Setup

### Pairing

Parent app creates:

- Short-lived QR payload.
- Six-digit fallback code.
- Expiration <=10 minutes.
- Single use.

Child app scans/enters and receives:

- Child device token.
- Family/profile binding.
- Public policy bootstrap.

### Android guided protection setup

The child app shows one Guardian-owned checklist screen, then launches each Android system authorization surface.

Required/strongly recommended components:

1. **VPN protection** - required for web/network filtering.
2. **Usage Access** - required for screen-time measurement.
3. **Accessibility protection** - required for strongest standard-mode app blocking and optional visible-text safety signals. Disclosure must explicitly state what is read and what stays local.
4. **Notification Access** - required only if Communication Safety from notification previews is enabled. It is optional at product level but recommended for relevant age bands.
5. **Notifications** - Guardian service/health notifications and child request responses.
6. **Battery optimization guidance** - request exemption only if justified by measured reliability; do not demand it before necessary.
7. **Always-on VPN guidance** - optional. If the device supports it, Guardian can deep-link/explain Android's always-on VPN setting, but standard Guardian cannot force the setting.

Setup screen:

```text
Set up protection

[check] Guardian paired
[ ] Web protection
[ ] App & time limits
[ ] App blocking
[ ] Communication safety (optional)
[ ] Notifications

About 2 minutes
```

Each line explains the benefit before opening system settings.

### iOS/iPadOS guided protection setup

1. Confirm device is signed in as the intended child Apple Account and belongs to a Family Sharing group when child authorization requires it.
2. Request Family Controls child authorization.
3. Parent/guardian approves Apple's authentication sheet on child device.
4. Configure Screen Time/Managed Settings.
5. Enable Guardian Network Extension content filter.
6. Enable Guardian notifications.
7. Sync policy.
8. Verify protection health.

If Apple Family Sharing is not correctly configured, show an actionable setup explanation and link the user into appropriate system settings/help. Do not present a generic error.

### Setup completion state

```text
Guardian is protecting this device

Apps & time       On
Web protection    On
Safety rules      On
Parent connection On

[Done]
```

---

## 8.4 Parent Home

### Objective

Parent understands family state in <=5 seconds.

### Phone layout

```text
Good evening

Family protected                         [Quick Control]

Emma                                     Protected
1h 42m today - 38m left
School routine ends at 4:00 PM
[+15 min]   [Pause]   [Open]

Arjun                                    Needs attention
Web protection is off
[Fix]

Requests
Emma wants 15 more minutes on YouTube
[Not now]                 [+15 min]

Today
3 unsafe sites blocked
1 new app reviewed
No high-risk safety events
```

### Home prioritization

Order:

1. Critical protection-health issue.
2. Pending urgent request.
3. Child summary cards.
4. Today protection summary.
5. Insights/trends.

Do not show marketing banners or upsells above protection status.

---

## 8.5 App Discovery, Classification, and Controls

### FR-APP-001 - App inventory model

Canonical app record:

```json
{
  "platform": "android",
  "platform_app_id": "com.example.app",
  "display_name": "Example",
  "category": "SOCIAL",
  "risk_tags": ["USER_GENERATED_CONTENT", "CHAT"],
  "age_guidance": "13+",
  "source": "DEVICE_OBSERVED",
  "reputation_version": 42
}
```

On iOS outside regions/API states that expose non-tokenized app data, Guardian stores opaque local aliases/tokens instead of exporting identifiable app inventory.

### FR-APP-002 - Android discovery

Preferred order:

1. `LauncherApps.getActivityList(null, currentUser)` for launchable applications.
2. `ACTION_PACKAGE_ADDED/REMOVED/REPLACED` and LauncherApps callbacks for changes.
3. Usage events and Accessibility package names for lazily observed packages.
4. Query a specific known package for label/version when allowed.
5. Avoid `QUERY_ALL_PACKAGES` as a mandatory architecture dependency. If later required, treat it as a separate Play-policy-reviewed capability.

### FR-APP-003 - iOS discovery

Use Family Controls selections/tokens and Device Activity/Managed Settings APIs. Do not assume the backend can obtain a complete named app inventory outside Apple's approved data-access conditions.

Where `approvedWithDataAccess` and `FamilyActivityData` are available, actual bundle identifiers/app lists are region-limited and must be capability-gated. As of the current Apple documentation, customer access to this non-tokenized data is limited to eligible EU devices/accounts.

### FR-APP-004 - App categories

Minimum taxonomy:

- Education.
- Productivity.
- Social.
- Messaging.
- Video/Streaming.
- Games.
- Browsers.
- Music/Audio.
- Shopping.
- Finance.
- Health/Fitness.
- Utilities.
- AI/Assistant.
- Dating.
- Gambling.
- Anonymous Chat.
- VPN/Proxy/Privacy Tools.
- Adult/Risky.
- Unknown.

### FR-APP-005 - App rule actions

Parent can choose:

- Always allow.
- Allowed within device schedule.
- Daily limit.
- Schedule only.
- Block.
- Ask parent.
- Temporary allow until time/date.

### FR-APP-006 - Essential apps

Allow parent to mark essential apps as unlimited/available during downtime:

- Phone/emergency system apps where applicable.
- School apps.
- Maps if parent chooses, despite location being out of Guardian scope.
- Authentication apps.

Guardian must not block critical operating-system functions needed to recover or manage the device.

### FR-APP-007 - New app policy

Age-band defaults:

- Young Child: notify + restrict until classified/parent decision where technically possible.
- Preteen: notify + apply category default immediately.
- Teen: apply category default + notify only if risk category/parent opted in.
- Older Teen: silent category policy except high-risk/blocked categories.

### App detail screen

```text
YouTube
Video & streaming

Today                    42 min
Daily limit              60 min
Allowed                  7 AM - 9 PM
Web/content protection   On

[Change daily limit]
[Change schedule]
[Block app]

Activity
...
```

No app configuration should require navigating through a global Settings maze.

---

## 8.6 Screen Time

### FR-TIME-001 - Device daily budget

Optional whole-device recreational budget. Do not count apps marked `always_allow` or `exclude_from_budget`.

### FR-TIME-002 - App daily budget

Per-app or app-category minutes.

### FR-TIME-003 - Session limit

Optional continuous-session cap for selected categories/apps.

Example:

- Games: 30 minutes per session.
- 15 minute cool-down.

Phase 2 if schedule pressure requires; data model must support it from Phase 1.

### FR-TIME-004 - Schedules

Support:

- Bedtime.
- School.
- Homework/Focus.
- Family time.
- Custom.

A routine contains:

```json
{
  "id": "routine_school",
  "name": "School",
  "schedule": {
    "days": [1,2,3,4,5],
    "start": "08:00",
    "end": "15:30"
  },
  "allowed_categories": ["EDUCATION", "PRODUCTIVITY"],
  "allowed_apps": [],
  "blocked_categories": ["GAMES"],
  "web_mode": "STRICT",
  "communication_mode": "ESSENTIAL_ONLY"
}
```

### FR-TIME-005 - Temporary grant

Parent can grant:

- +5 min.
- +15 min.
- +30 min.
- +1 hour.
- Until selected time.
- Rest of day.

Temporary grant must be possible in <=2 interactions from child Home card or request notification.

### FR-TIME-006 - Time warnings

Child notifications/in-app signals:

- 15 min remaining.
- 5 min remaining.
- 1 min remaining.

Warnings are configurable and age-adaptive.

### FR-TIME-007 - Time expiration

At expiration:

- iOS: apply Managed Settings shield for token/category.
- Android: local policy marks app blocked; Accessibility enforcement displays Guardian block surface and exits/obscures app; VPN denies network for blocked app where configured.

Child sees:

```text
Time is up for YouTube
You've used 1 hour today.

[Ask for 15 more minutes]
[Done]
```

---

## 8.7 Routines

### Required built-in routines

- Bedtime.
- School.
- Homework/Focus.
- Family Time.

Parent can create custom routines.

### One-tap modes

From Quick Control:

```text
Start now

School
Focus
Family Time
Bedtime
Custom
```

Starting a routine manually creates a temporary policy overlay with an explicit end condition.

### Rule precedence

Highest to lowest:

1. System safety exceptions/critical allowlist.
2. Temporary explicit parent allow/block.
3. Active manual routine.
4. Scheduled routine.
5. Explicit app/domain rule.
6. Age/content profile rule.
7. Category default.
8. Unknown-content default.

A deny normally wins over allow unless the higher-precedence rule explicitly grants access.

---

## 8.8 Web and Network Protection

### Product requirement

Filtering must apply regardless of browser and regardless of whether a link is opened inside another app, to the extent the OS network stack exposes the destination.

### FR-WEB-001 - Local category database

Minimum categories:

- Adult/Pornography.
- Sexual content.
- Gambling.
- Drugs/Controlled substances.
- Alcohol/Tobacco.
- Graphic violence/Gore.
- Self-harm/Suicide.
- Hate/Extremism.
- Weapons.
- Malware.
- Phishing/Scams.
- Anonymous chat.
- Dating.
- Proxy/VPN/Tor/bypass.
- Piracy.
- Social media.
- Streaming/video.
- Games.
- Shopping.
- AI assistants.
- Education.
- Search engines.
- News.
- Unknown/newly observed.

### FR-WEB-002 - Decision layers

Every request follows:

```text
1. Emergency/system bypass safety check
2. Parent explicit domain rule
3. Local domain reputation cache
4. Local category bundle/trie/Bloom filter
5. Current routine and age policy
6. Unknown policy
7. Optional asynchronous cloud classification
```

### FR-WEB-003 - Unknown domain behavior

Young child/preteen strict policy:

- Unknown high-risk or newly registered domain: block pending classification.
- Neutral unknown domain: configurable; strict mode blocks briefly, balanced mode permits while classifying.

Teen/older teen default:

- Allow neutral unknown domains while classification happens asynchronously.
- Block domains with risk indicators.

### FR-WEB-004 - Parent domain rule

Parent can:

- Always allow.
- Always block.
- Allow for one hour.
- Allow today.
- Allow during selected routine.

### FR-WEB-005 - Block UX

When OS/browser filtering supports a Guardian remediation page, show:

```text
This page is blocked

Reason: Gambling content
Rule: Web Safety - Age 11

[Ask Parent]
[Go Back]
```

When the OS can only fail the network connection, send a local child notification/in-app event with the same explanation when possible.

### FR-WEB-006 - No TLS MITM

Guardian categorizes using:

- DNS/domain.
- Destination network metadata.
- TLS-visible metadata when lawfully/system-exposed.
- Apple URL filter/full URL APIs where available.
- Browser/Accessibility visible URL only when explicitly enabled and safely available.
- Cloud public-web enrichment for the domain/URL, not intercepted private payload.

### FR-WEB-007 - Bypass resistance

Detect/classify:

- Public VPN providers.
- Proxy services.
- Tor entry/service domains where reputation data permits.
- Encrypted DNS resolver endpoints.
- Browser-integrated proxy services where identifiable.

Do not try to break encryption. Apply destination/app rules.

### FR-WEB-008 - Safe search

Guardian should enforce or recommend safe-search modes where a standards-based/domain/query approach is practical. Do not make per-search-engine private API integration a dependency for V1.

---

## 8.9 Content Intelligence

### Objective

Convert heterogeneous signals into a consistent safety verdict.

### Safety taxonomy

```text
ADULT_NUDITY
SEXUAL_CONTENT
GROOMING_RISK
BULLYING_HARASSMENT
HATE_EXTREMISM
SELF_HARM_SUICIDE
GRAPHIC_VIOLENCE
VIOLENCE
DRUGS
ALCOHOL_TOBACCO
GAMBLING
WEAPONS
DANGEROUS_CHALLENGE
ANONYMOUS_CHAT
SCAM_FRAUD
MALWARE_PHISHING
STRONG_LANGUAGE
AGE_INAPPROPRIATE
PARENT_CUSTOM_RULE
UNKNOWN
```

### Verdict schema

```json
{
  "action": "ALLOW | BLOCK | WARN | REVIEW",
  "category": "SELF_HARM_SUICIDE",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "confidence": 0.97,
  "signal_types": ["DOMAIN_REPUTATION"],
  "reason_code": "KNOWN_HIGH_RISK_DOMAIN",
  "ttl_seconds": 86400,
  "policy_version": 92
}
```

### Signal hierarchy

1. Parent explicit rule.
2. Curated/reputable deterministic safety dataset.
3. App/domain reputation.
4. On-device deterministic text patterns.
5. On-device lightweight ML classifier.
6. Cloud public-content classifier for unknown public destinations.
7. Parent review for ambiguous high-impact cases.

### AI rules

- Do not call an LLM for every website/app event.
- Do not send private notification/message content to cloud by default.
- AI must return structured output validated against schema.
- High-impact automated blocks should have deterministic/category support or a high-confidence model threshold.
- Classifier versions are recorded.
- Parents can report false positives/false negatives.

---

## 8.10 Communication Safety

### Product naming

Use **Communication Safety** or **Communication Risk Signals**.

Do not market it as "read all messages".

### Android - notification signals

If parent enables the feature and child-device notification access is granted:

`NotificationListenerService` receives notifications posted/removed by Android.

Local processor extracts only necessary transient fields such as:

- Source package.
- Notification category/channel where available.
- Title/text/subtext when exposed.
- Timestamp.

Then immediately runs local classification.

Default persistence:

```text
raw notification text: NOT persisted
raw notification text: NOT uploaded
persisted event: category + severity + source app + timestamp + confidence + reason code
```

Optional parent-visible evidence must be a future separately consented feature and is not required for launch.

### Android - Accessibility signals

When explicitly enabled, Accessibility can provide active-window events and accessible text nodes.

Use only for:

1. Detecting foreground blocked app and presenting app-block UX.
2. Optional local safety classification of visible text in the active app.
3. Browser/address information where reliably exposed.
4. Tamper/degraded-state protection UX where Play policy allows and disclosure is explicit.

Never use Accessibility to:

- Secretly click through consent dialogs.
- Grant itself permissions.
- Circumvent Android security controls.
- Automate unrelated user actions.
- Harvest full UI trees into the cloud.

### iOS communication-safety ceiling

Guardian cannot read arbitrary third-party notification content or message bodies through public iOS APIs.

On iOS, Communication Safety consists of:

- App/category usage signals.
- Source-app network flow metadata.
- Destination domain/URL risk where available.
- Unsafe-link blocking.
- Time/schedule controls.
- Parent restrictions on high-risk app categories.

Any UI describing an unavailable iOS signal must say `Not available on iPhone/iPad` rather than silently showing zero events.

### Risk event behavior

Default parent notification thresholds:

- CRITICAL: immediate.
- HIGH: immediate or bundled within minutes depending on type.
- MEDIUM: daily summary unless parent opts in.
- LOW: analytics/trend only.

Critical examples:

- High-confidence self-harm risk.
- High-confidence grooming/sexual solicitation risk.
- Known malware/phishing credential theft.

The product must avoid flooding parents based on a single ambiguous word.

---

## 8.11 Requests and Approvals

### Request types

- More time.
- Open blocked app.
- Open blocked website.
- Install/use new app decision.
- Temporarily change routine.

### Child request flow

From a block screen:

```text
[Ask Parent]
       ↓
Choose request
  15 min
  30 min
  Until 8 PM
       ↓
Optional short reason
       ↓
Send
```

Keep optional reason to one line; do not force essay-like justification.

### Parent request card

```text
Emma wants 15 more minutes
YouTube
58 min used today - daily limit 60 min

[Not now]                [+15 min]
```

For websites:

```text
Emma wants to open example.com
Category: Unknown
Guardian confidence: Low risk / still checking

[Block] [Allow once] [Always allow]
```

### Approval propagation

- Foreground: WebSocket/realtime channel.
- Background: push notification + backend state.
- Child periodically reconciles unresolved requests in case realtime delivery fails.
- Approval is idempotent.
- Expired requests cannot be resurrected.

---

## 8.12 Activity and Reports

### Principle

Default activity is a summary, not a surveillance log.

### Parent activity home

```text
Today - Emma

2h 16m screen time

Education       51m
Entertainment   42m
Games           31m
Social          12m

Protection
7 unsafe sites blocked
2 unknown sites reviewed
0 high-risk events

Requests
3 approved
1 declined
```

### Drill-down

- App/category usage.
- Time-of-day distribution.
- Web category blocks.
- New apps.
- Safety events.
- Requests.
- Protection-health incidents.

### Age-adaptive reporting

Young child:

- Parent gets more detail.
- Child gets simple time-left view.

Teen/older teen:

- Child gets their own week trends.
- Parent default shifts toward aggregate time/category and meaningful safety events.

### iOS reporting caveat

Do not architect the parent dashboard around unrestricted export of Apple's detailed per-app Screen Time data. Apple's Device Activity reporting is privacy-preserving and some non-tokenized/export APIs are region-limited. Guardian can still synchronize Guardian-owned policy events, block outcomes, network risk events, and permitted aggregate data.

---

## 8.13 Protection Health

### Health model

```json
{
  "overall": "HEALTHY | DEGRADED | OFFLINE | NEEDS_ACTION",
  "network_filter": "ACTIVE | DISABLED | ERROR | UNKNOWN",
  "usage_access": "ACTIVE | DISABLED | NA",
  "app_blocking": "ACTIVE | DISABLED | LIMITED | NA",
  "communication_safety": "ACTIVE | DISABLED | LIMITED | NA",
  "family_controls": "AUTHORIZED | DENIED | NA",
  "policy_version": 92,
  "policy_current": true,
  "last_sync_at": "...",
  "service_heartbeat_at": "..."
}
```

### Parent card

Healthy:

```text
Protected
Everything is working normally.
```

Degraded:

```text
Protection needs attention
App blocking permission is off on Emma's Android phone.
[Fix]
```

### Child card

```text
Guardian needs permission
Ask your parent to finish protection setup.
```

### Health alerts

Trigger parent alert when:

- Android VPN revoked/stopped for meaningful duration.
- Usage Access removed.
- Accessibility removed when required.
- Notification Access removed when Communication Safety enabled.
- iOS Family Controls authorization revoked.
- iOS content filter unavailable.
- Policy is stale beyond threshold.
- Child device has not checked in for configured period.

Avoid alerting every transient service restart.

---

## 8.14 Tamper and Circumvention Handling

### Android standard mode

Because Guardian intentionally avoids Device Owner enrollment, no claim of absolute anti-tamper is allowed.

Use layered best effort:

- Detect permission removal.
- Detect service stop/revocation.
- Notify parent.
- Show persistent child-device health reminder.
- If Accessibility is enabled, detect attempts to open Guardian uninstall/app-info/protection setting surfaces where technically and policy-compliantly possible, and present a transparent parent-authorization warning.
- Detect known VPN/proxy bypass apps/services through app/network risk classification.
- Encourage Android's user-configurable Always-on VPN setting during setup.

Do not lock the user out of system recovery or emergency functions.

### iOS

Rely on Family Controls authorization semantics. Apple documents that child authorization can prevent the child from deleting the parental-control app and signing out of iCloud while an authorized parental-control app is active.

---

## 8.15 Notifications

### Parent notification taxonomy

**Critical Safety**

- High-confidence critical content/risk.

**Protection Health**

- Filtering disabled.
- Permission revoked.

**Request**

- Child asks for time/site/app.

**Informational**

- New app installed/observed.
- Weekly report ready.

### Notification rules

- Alerts must be actionable.
- Bundle repetitive website blocks.
- Do not send a notification for every ordinary denied connection.
- Respect parent quiet hours except critical safety/protection-health events as configured.
- No sensitive child content in lock-screen notification text by default.

Example:

> Guardian safety alert - Emma  
> A high-risk communication signal needs your attention. Open Guardian for details.

Not:

> Emma received: "[private message text...]"

---

## 8.16 Settings

Required settings:

### Family

- Family name.
- Guardians.
- Children.
- Devices.
- Unpair device.

### Protection

- Default age policy.
- Unknown content behavior.
- Communication Safety.
- Protection-health alerts.

### Privacy

- Data collected.
- Local-only content explanation.
- Activity retention.
- Export family data.
- Delete child history.
- Delete child profile.
- Delete account.

### Notifications

- Requests.
- Safety.
- Protection health.
- Reports.

### Appearance/accessibility

- Follow system appearance by default.
- Optional reduced data visualization density.
- Do not recreate system accessibility controls; honor platform settings.

### Help

- Protection troubleshooting.
- Android permissions.
- Apple Family Sharing.
- Why Guardian cannot see certain iOS content.
- Contact support.

---

# 9. Interaction Design and Critical User Flows

## 9.1 Flow: Add child and pair device

```text
Parent Home
  -> Add Child
  -> Name + age
  -> Recommended policy
  -> QR/code

Child device
  -> Child role
  -> Scan QR/code
  -> Protection setup
  -> Protected

Parent Home updates in real time
```

Acceptance:

- Pairing code cannot be reused.
- Parent can cancel pairing.
- Wrong family code does not leak child/family details.
- Device has clear recovery if setup is interrupted.

## 9.2 Flow: Change app limit

```text
Home
 -> Child card
 -> Apps
 -> YouTube
 -> Daily limit sheet
```

This path is technically four navigations if counted naively, so Home child card must expose contextual search/quick actions and the 3-Interaction Law requires one of these valid routes:

```text
Home -> Quick Control -> "YouTube limit" -> Save
```

or

```text
Home -> Child -> Apps -> choose app with inline edit action
```

Where selecting the app and opening its inline editor is considered the third deliberate navigation/action before the edit itself. The product analytics checker should count route depth separately from control interaction.

### UX interpretation of the law

The law is about finding/reaching capability, not counting each keystroke or selecting the final value.

## 9.3 Flow: Child asks for more time

```text
Blocked/time-up screen
 -> Ask Parent
 -> +15 min
```

Parent:

```text
Push notification
 -> +15 min action
```

No app open required for common approval when secure notification actions are available.

## 9.4 Flow: Block site from activity

```text
Activity
 -> Web
 -> Domain event
 -> Always Block
```

Alternative:

```text
Quick Control
 -> type domain
 -> Block
```

## 9.5 Flow: Protection disabled

Parent:

```text
Home
 -> "Needs attention"
 -> Fix instructions/deep link
```

Child device should also show guided remediation.

## 9.6 Flow: High-risk communication signal

Android:

```text
Notification/UI signal
 -> local classifier
 -> HIGH/CRITICAL event
 -> store only minimized event
 -> parent push
 -> Guardian Safety Event
```

Parent event includes:

- Child.
- App/category.
- Risk type.
- Time.
- Confidence band, not misleading pseudo-precision.
- Recommended parent action.
- Explicit statement if Guardian did not retain message text.

## 9.7 Flow: App opens after time expired - Android

```text
Accessibility window event / usage event
 -> identify package
 -> local policy lookup
 -> BLOCK
 -> Accessibility overlay or Guardian block activity
 -> optional GLOBAL_ACTION_HOME/back as supported
 -> network denied for package while blocked
```

The block surface must appear quickly enough that the child cannot meaningfully use the blocked app before enforcement.

Target: p95 <500 ms from detectable foreground transition to visible block surface on supported devices.

## 9.8 Flow: App opens after time expired - iOS

Managed Settings shield should already be active based on Device Activity threshold/scheduled policy. The system shield appears instead of the app content.

## 9.9 Undo and reversibility

Parent policy changes that can be easily reversed should support transient `Undo` toast where appropriate.

Destructive operations requiring confirmation:

- Remove child.
- Unpair device.
- Delete history.
- Delete family/account.

Changing an app limit does not need a confirmation alert.

---

# 10. Android Technical Architecture

## 10.1 Supported Android baseline

- Minimum Android: Android 10 / API 29 unless implementation testing reveals an unavoidable dependency requiring a higher baseline.
- Target/compile SDK: latest stable required by Google Play at implementation/release time.
- Test priority: Android 11 through current Android version, phones and tablets.

Reason for Android 10 baseline: provides modern VPN/network ownership capabilities while retaining reasonable older child-device coverage.

## 10.2 Android native components

```text
Guardian Android

Main React Native Activity
    |
    +-- GuardianProtectionModule (Expo Module)
    |
    +-- GuardianVpnService
    |     +-- TunInterface
    |     +-- PacketForwarder
    |     +-- DnsInspector
    |     +-- FlowAttribution
    |     +-- DomainPolicyEngine
    |
    +-- GuardianAccessibilityService
    |     +-- ForegroundAppObserver
    |     +-- BlockOverlayController
    |     +-- OptionalVisibleTextRiskProcessor
    |
    +-- GuardianNotificationListenerService
    |     +-- NotificationRiskProcessor
    |
    +-- UsageRepository
    |     +-- UsageStatsManager
    |     +-- UsageEventsProcessor
    |
    +-- AppInventoryRepository
    |     +-- LauncherApps
    |     +-- Package change receiver/callbacks
    |
    +-- LocalPolicyStore
    +-- PolicyEvaluator
    +-- PolicySyncWorker
    +-- ProtectionHealthMonitor
    +-- EventOutbox
```

## 10.3 Expo bridge design

Expose coarse APIs only.

```ts
interface GuardianProtectionNative {
  getCapabilities(): Promise<PlatformCapabilities>;
  getProtectionStatus(): Promise<ProtectionStatus>;
  requestVpnPermission(): Promise<PermissionResult>;
  openUsageAccessSettings(): Promise<void>;
  openAccessibilitySettings(): Promise<void>;
  openNotificationAccessSettings(): Promise<void>;
  startProtection(): Promise<void>;
  applyPolicyBundle(bundle: SignedPolicyBundle): Promise<ApplyResult>;
  getUsageSummary(range: TimeRange): Promise<UsageSummary>;
  getObservedApps(): Promise<ObservedApp[]>;
  subscribe(listener: (event: GuardianNativeEvent) => void): Subscription;
}
```

Do not expose packet-level callbacks to JS.

## 10.4 VpnService

### Responsibilities

- Create TUN interface.
- Route selected/all app traffic through local filtering path.
- Inspect DNS requests/responses.
- Track destination IP/port/protocol.
- Correlate domain -> connection when feasible.
- Attribute flows to source application where Android APIs permit.
- Apply local domain/app network policy.
- Forward allowed traffic without routing raw content through Guardian cloud.
- Emit minimized block/health events.

### Foreground service requirement

VpnService must comply with Android foreground service lifecycle rules and show the required persistent system notification while active.

### Always-on

Guardian declares support for Android's always-on VPN feature. Standard consumer setup may guide the parent/child to enable it in Android Settings. Guardian does not claim it can force lockdown without device/profile owner privileges.

### Per-app network rules

Use source UID/package attribution and/or VpnService allowed/disallowed application configuration only where it improves enforcement.

Important: rebuilding the VPN to change allowed/disallowed application lists can be disruptive. Prefer routing all child traffic through the local TUN and enforcing in the local policy engine rather than constantly rebuilding per-app VPN allowlists.

## 10.5 Flow attribution

Use Android connection ownership APIs where supported to map TCP/UDP flow tuples to UID. Map UID to package(s). Handle shared UID edge cases conservatively.

Cache mapping:

```text
flow tuple -> uid -> package set
```

If attribution is unavailable:

- Still apply destination/domain policy.
- Mark app source as unknown.
- Do not invent app attribution.

## 10.6 DNS handling

Preferred strategy:

- Capture normal DNS traffic through TUN.
- Maintain query/response correlation cache.
- Use domain category decision before permitting subsequent connection when feasible.
- Detect known DoH/DoT resolver endpoints and apply bypass policy.

Do not require Guardian-owned remote DNS for all users if local filtering can work; a Guardian resolver may be introduced later as an optional optimization.

## 10.7 Packet forwarding implementation

For speed, select a proven user-space TUN forwarding approach/library with compatible licensing rather than writing a production TCP/IP stack from scratch unless engineering already has a reliable implementation.

Requirements:

- IPv4 and IPv6.
- TCP and UDP.
- DNS.
- QUIC/UDP 443 forwarding.
- NAT/socket lifecycle.
- No unnecessary packet copies.
- Backpressure.
- Crash isolation.
- Battery profiling.

Do not block QUIC globally merely because inspection is harder; use domain/DNS policy and reputation.

## 10.8 UsageStatsManager

Required user-granted Usage Access.

Use:

- `queryEvents` for foreground/background state changes.
- Aggregate usage for daily/session budgets.
- Local daily rollover in child timezone.

Persist local summarized usage, not high-frequency event spam.

## 10.9 App inventory

Use LauncherApps to enumerate launchable apps and monitor app changes without making broad package visibility a mandatory dependency.

Store locally:

```text
package_name
display_name
icon cache reference
first_seen_at
last_seen_at
category
policy
```

Sync only necessary app identity/category/policy data to parent account with clear disclosure.

## 10.10 NotificationListenerService

### Permission

User must explicitly grant Notification Access in Android Settings.

### Processor

For each posted notification:

```text
1. Check source app against communication-safety scope.
2. Extract minimal exposed text in memory.
3. Normalize language/script.
4. Run local pattern classifier.
5. If ambiguous and on-device ML available, run local model.
6. Produce structured risk event.
7. Zero/discard raw text after classification.
8. Persist only minimized event.
9. Push parent notification only above configured severity threshold.
```

### Exclusions

Ignore:

- Guardian notifications.
- System noise.
- Media playback notifications unless relevant to content policy.
- Authentication OTPs/password reset codes from risk analysis where detectable.
- Financial transaction messages from communication-safety analysis unless parent explicitly enables scam risk; never persist sensitive amounts/account identifiers unnecessarily.

## 10.11 AccessibilityService

### Why it exists

In standard consumer Android, there is no Device Owner power to suspend arbitrary apps. Accessibility provides the strongest practical non-enterprise path for:

- Detecting foreground app transitions rapidly.
- Showing a blocking accessibility overlay.
- Returning the user to Home/back when a blocked app appears.
- Optional local analysis of visible accessible text.

### Required Google Play posture

This is not an `isAccessibilityTool` disability app. Guardian must:

- Declare Accessibility use in Play Console.
- Present prominent in-app disclosure immediately before enabling.
- Obtain affirmative parent/guardian consent.
- Explain exact data use.
- Use narrower APIs when possible.
- Keep Accessibility features limited to core parental-control functionality.

### Block overlay

Use `TYPE_ACCESSIBILITY_OVERLAY` or platform-appropriate Accessibility overlay mechanisms where permitted.

Block surface:

- Covers blocked app.
- Shows Guardian reason/time state.
- Provides Ask Parent.
- Prevents interaction with underlying blocked app while overlay is active.
- Returns to launcher/home when dismissed if policy remains blocked.

### UI-text analysis

Only inspect active-window node text when Communication Safety Advanced is enabled.

Do not continuously traverse entire trees at high frequency. Trigger on meaningful window/content events with debounce.

Some apps render inaccessible/canvas content. Mark signal coverage as partial.

## 10.12 Android policy evaluator

Native synchronous API:

```kotlin
data class PolicyContext(
    val now: Instant,
    val childId: String,
    val packageName: String?,
    val domain: String?,
    val destinationIp: String?,
    val usageTodayMs: Long?,
    val sessionMs: Long?,
    val activeRoutineIds: Set<String>,
    val signal: SafetySignal?
)

data class PolicyDecision(
    val action: Action,
    val reasonCode: String,
    val expiresAt: Instant?,
    val policyVersion: Long
)
```

Hot path is deterministic and thread-safe.

## 10.13 Android local storage

Use encrypted database/preferences for sensitive local state.

Recommended:

- SQLite/Room for structured local data.
- Android Keystore for device keys.
- Encrypted secret/token storage.
- File-based compact domain cache for high-throughput lookups if SQLite proves too slow.

## 10.14 Android background work

Use:

- Foreground service for VPN.
- WorkManager for policy sync, event upload, maintenance, and retry.
- System callbacks for package/network state.

Do not implement aggressive 1-second polling loops.

## 10.15 Android failure modes

### VPN permission revoked

- Health -> NEEDS_ACTION.
- Parent alert after debounce.
- Child setup reminder.
- Web filtering unavailable; app/time controls continue where possible.

### Accessibility disabled

- Health -> DEGRADED.
- Time measurement can continue through UsageStats.
- Network block can continue.
- Strong visual app blocking and visible-text signals unavailable.

### Usage Access disabled

- Health -> DEGRADED.
- Existing network/app static rules continue.
- Time budgets cannot be trusted; do not fabricate remaining time.

### Notification Access disabled

- Communication Safety -> LIMITED.
- Do not call it healthy.

### Process killed

- VPN foreground service follows OS lifecycle.
- WorkManager/restart mechanisms recover where allowed.
- Parent health uses heartbeat, not assumption.

---

# 11. iOS and iPadOS Technical Architecture

## 11.1 Supported Apple baseline

- Minimum deployment target: iOS/iPadOS 16 unless implementation validation recommends 17+ to materially reduce complexity.
- Enhanced URL filtering capability: conditionally use iOS 26+ Network Extension URL Filter.
- Use latest stable Xcode supported for App Store submission at implementation time.

## 11.2 Native project strategy

Do not rely solely on Expo Continuous Native Generation for critical Apple app extensions because Expo's CNG app-extension workflow remains an area with experimental support.

Recommended:

1. Start from the Expo/React Native project.
2. Generate native projects once.
3. Commit `ios/` and `android/`.
4. Add and maintain Xcode extension targets directly.
5. Use Expo Development Builds for rapid JS iteration.
6. Use EAS Build or Xcode CI with multi-target credentials.

## 11.3 Required Apple frameworks

- FamilyControls.
- ManagedSettings.
- DeviceActivity.
- ManagedSettingsUI.
- NetworkExtension.
- UserNotifications for Guardian's own notifications.
- App Groups for permitted shared configuration between host app/extensions.

## 11.4 Required iOS extension targets

Baseline targets:

```text
Guardian.app
GuardianDeviceActivityMonitor.appex
GuardianShieldConfiguration.appex
GuardianShieldAction.appex
GuardianFilterData.appex
GuardianFilterControl.appex
GuardianDeviceActivityReport.appex   (if used for local privacy-preserving reports)
```

Conditional iOS 26+ URL filter extension/configuration may be added if implementation requires an extension target for control provider under Apple's URL Filter API.

Each relevant target must have the correct Family Controls/Network Extension/App Group entitlements.

## 11.5 Family Controls authorization

Child setup calls Apple Family Controls authorization for the child device.

Requirements:

- Child is in appropriate Apple Family Sharing configuration for child authorization.
- Parent/guardian approves Apple system authentication sheet.
- Guardian checks authorization status continuously/reasonably.
- Revocation changes health state.

Distribution requires Apple approval for the Family Controls entitlement for app and relevant Screen Time extensions.

## 11.6 Managed Settings

Use `ManagedSettingsStore` to apply:

- App shields.
- App-category shields.
- Web-domain shields.
- Web-domain-category policies where supported.
- Relevant device restrictions supported for the parental-control use case.

Guardian should create named stores by concern where that improves rule composition, but keep precedence understandable.

Suggested:

```text
store.baseAgePolicy
store.scheduledRoutine
store.temporaryParentOverride
store.timeBudget
```

Have a deterministic reconciliation layer decide what each store should contain rather than arbitrary writes from multiple screens.

## 11.7 Device Activity

Use DeviceActivity for:

- Scheduled routines.
- Usage thresholds.
- Daily limits.
- Warning thresholds.
- Activity report UI where appropriate.

Device Activity extensions must update Managed Settings even when the host app is not open.

### Monitor naming

Use stable versioned identifiers:

```text
guardian.child.<profile>.daily
guardian.child.<profile>.routine.<id>
guardian.child.<profile>.appbudget.<policyid>
```

Handle OS-imposed limits on monitor/event count by grouping policies intelligently rather than creating unbounded monitors.

## 11.8 App identity and privacy

Outside specific approved/region-limited data-access APIs, Family Controls uses opaque tokens to represent apps, categories, and web domains.

Guardian design must work when:

- Backend does not know the app's bundle ID/name.
- A policy is represented by an opaque token/alias local to the authorized Apple environment.

### Local alias model

```text
local_policy_target_id
token_blob (local encrypted storage)
display_label (only where system lets Guardian render/resolve it)
parent_facing_alias
category_token
```

Do not reverse engineer tokens.

### EU enhanced data

Apple's newer FamilyActivityData/non-tokenized access is region-limited in current documentation. Treat it as an enhancement, never as core global architecture.

## 11.9 Network Extension content filter

Use a content filter provider for authorized child devices.

Architecture:

```text
Guardian host/control sync
   -> Filter Control Provider
   -> shared read-only rules/database
   -> Filter Data Provider
   -> allow/block flow locally
```

Apple intentionally sandboxes the Filter Data Provider so network content cannot be freely exported. Guardian embraces this.

### Filter responsibilities

- Inspect flow metadata.
- Access source app identifier/version when provided.
- Apply local domain/network policy.
- Generate block/remediation verdicts.
- Record minimized local event through permitted provider reporting/sharing mechanisms.

Do not attempt to make network calls from the data provider sandbox.

## 11.10 iOS 26+ URL Filter

When available and entitlement/deployment requirements are satisfied, use Network Extension URL Filter for performant full-URL checks for WebKit and URLSession traffic.

Important limitations:

- It covers URL requests through WebKit and URLSession automatically.
- Apps using other networking stacks must voluntarily participate for full URL checks.
- Therefore it enhances universal coverage but does not magically expose every URL from every app.

Use a local Bloom filter + privacy-preserving remote lookup architecture as supported by Apple's API rather than inventing a custom leakier URL service.

## 11.11 NEFilterFlow source app metadata

When provided, use:

- `sourceAppIdentifier`.
- `sourceAppVersion`.
- Flow direction.
- HTTP URL when available on the flow type.

Do not assume every flow has every property.

## 11.12 iOS communication safety limitation

Apple's UserNotifications service extensions operate on notifications for the app that owns the extension/notification, not arbitrary third-party notifications. Guardian therefore has no supported general cross-app notification reader on iOS.

Implementation rule:

```text
if platform == iOS:
    communicationSafety.messageBodyInspection = unavailable
```

Do not attempt private APIs, notification database access, screen scraping, or ReplayKit-based continuous surveillance.

## 11.13 iOS child app deletion protection

When Family Controls child authorization is active, rely on Apple's documented parental-control protections rather than creating custom anti-uninstall hacks.

## 11.14 iOS shared storage

Use App Groups only for data that Apple permits extensions to share.

Separate:

- Host app database.
- Extension configuration snapshots.
- Signed policy bundle.
- Small event queues where allowed.

Respect DeviceActivityReport sandbox restrictions; sensitive Screen Time report data must not be exported through unsupported paths.

## 11.15 iOS failure modes

### Family Controls denied/revoked

- Health -> NEEDS_ACTION.
- Managed Settings/Device Activity policies cannot be trusted.
- Parent alert.
- Guided reauthorization.

### Content filter disabled/error

- Web protection -> DEGRADED.
- Screen Time app rules continue.
- Parent alert after debounce.

### App Group/policy unavailable in extension

- Use last valid policy if available.
- Conservative age-default fallback for clearly blocked categories where possible.
- Record health event.

### Child not in compatible Family Sharing setup

- Setup cannot claim completion.
- Show exact requirement and remediation.

---
# 12. Shared Policy Architecture

## 12.1 Canonical policy document

Cloud is the source of desired family policy. Child device is the source of enforcement truth.

Canonical bundle:

```json
{
  "schema_version": 1,
  "policy_version": 194,
  "family_id": "fam_123",
  "child_profile_id": "child_456",
  "issued_at": "2026-08-14T12:00:00Z",
  "expires_soft_at": "2026-08-21T12:00:00Z",
  "age_band": "PRETEEN",
  "base_policy": {},
  "app_rules": [],
  "domain_rules": [],
  "category_rules": [],
  "routines": [],
  "temporary_overrides": [],
  "communication_safety": {},
  "signature": "base64..."
}
```

### Signature

Use an asymmetric signature so the child device can reject tampered policy bundles.

Recommended: Ed25519 unless platform/library constraints suggest another standard algorithm.

The backend signing private key is never shipped to clients.

## 12.2 Policy compilation

Cloud policy can be expressive. Native hot-path representation should be compiled/minimized.

Example:

```text
Canonical JSON policy
       ↓
Native compiler
       ↓
CompiledPolicySnapshot
       ├── app lookup map
       ├── category lookup
       ├── domain trie/Bloom/cache
       ├── schedule intervals
       └── temporary overrides
```

Apply bundle atomically:

1. Verify signature.
2. Validate schema/version.
3. Compile.
4. Store new snapshot.
5. Swap active snapshot atomically.
6. Acknowledge applied version.
7. Keep previous valid snapshot for rollback.

## 12.3 Decision precedence

Canonical precedence:

```text
Safety/system allowlist
    > temporary explicit parent override
    > active manual routine
    > active scheduled routine
    > explicit target rule
    > age-band hard category rule
    > default category rule
    > unknown policy
```

Log `reason_code` and `policy_rule_id` for every user-visible block.

## 12.4 Time evaluation

All schedules are stored in child's configured IANA timezone.

Handle:

- Daylight saving time.
- Device timezone changes.
- Parent travel/change.
- Midnight rollover.
- Clock rollback/forward.

Use server time for synchronization but local monotonic time for session duration where possible.

---

# 13. Backend Architecture

## 13.1 Goals

Backend provides:

- Identity/family/device management.
- Policy storage and versioning.
- Signed policy bundle generation.
- Device sync.
- Parent/child requests.
- Push/realtime delivery.
- App/domain reputation.
- Public-content classification.
- Minimized event ingestion.
- Reports/aggregation.
- Protection health.

Backend must not become a required proxy for all child internet traffic.

## 13.2 Recommended stack

Reuse the prototype's productive stack where it accelerates delivery:

- Python 3.13+.
- FastAPI.
- PostgreSQL / Supabase Postgres.
- Supabase Auth or equivalent managed auth.
- WebSocket/realtime channel.
- Redis only if/when needed for cache/rate limiting; avoid adding it before real need.
- Object storage only for non-sensitive generated reports/assets; not raw child traffic.

## 13.3 Service boundaries

Start as a modular monolith, not microservices.

```text
backend/
  app/
    auth/
    families/
    children/
    devices/
    policies/
    requests/
    events/
    health/
    reputation/
    classification/
    notifications/
    reports/
```

Split services later only under measured scale/ownership need.

## 13.4 Core database tables

### parents

```text
id
email
display_name
created_at
```

### families

```text
id
name
owner_parent_id
created_at
```

### family_guardians

```text
family_id
parent_id
role
created_at
```

### child_profiles

```text
id
family_id
display_name
birth_date_or_age_data
age_band
timezone
created_at
```

Minimize birth-date storage. If exact DOB is unnecessary, store year/month or derived age with next-age-transition date.

### devices

```text
id
family_id
child_profile_id
role
platform
platform_version
app_version
public_key
capabilities_json
protection_state_json
policy_version_applied
last_seen_at
revoked_at
```

### policy_documents

```text
id
child_profile_id
version
policy_json
created_by_parent_id
created_at
```

### policy_bundles

```text
child_profile_id
version
bundle_hash
signature
issued_at
```

### requests

```text
id
child_profile_id
device_id
type
target_type
target_ref
duration_requested
reason_short
status
created_at
expires_at
resolved_at
resolved_by_parent_id
resolution_json
```

### safety_events

```text
id
child_profile_id
device_id
platform
source_type
source_app_ref_minimized
category
severity
confidence_band
reason_code
occurred_at
classifier_version
raw_content_retained=false
metadata_json_minimized
```

### web_events

Persist only meaningful events, not every connection.

```text
id
child_profile_id
domain_or_privacy_preserving_ref
category
action
reason_code
occurred_at
source_app_ref_minimized
policy_version
```

### usage_aggregates

```text
child_profile_id
local_date
app_or_category_ref
minutes
platform
```

Respect iOS export/privacy limitations; table content differs by capability.

### protection_health_events

```text
id
device_id
component
state
occurred_at
resolved_at
```

## 13.5 Pairing security

Pairing code payload must include:

- Random high-entropy token, QR encoded.
- Human fallback six-digit code maps server-side to token.
- TTL <=10 minutes.
- Single use.
- Family/child binding server-side.
- Rate limiting.
- Attempt limiting.

Device generates local keypair before/at pairing and registers public key.

## 13.6 Device authentication

Use revocable device credential separate from parent JWT.

Device auth requirements:

- Scoped to one device/profile.
- Rotate/revoke.
- Key stored in platform secure store.
- No parent privileges.
- Request signing or token binding desirable.

## 13.7 Realtime

Event types:

```text
policy.updated
policy.applied
request.created
request.resolved
protection.health_changed
safety.high_risk
child.online
child.offline
```

WebSocket for foreground responsiveness; push/reconciliation for background reliability.

## 13.8 Push

- FCM for Android.
- APNs for iOS through either direct backend integration or a production-appropriate Expo notification path.
- Store push token per parent/child device.
- Avoid private content in push payload.

## 13.9 Rate limiting

Apply to:

- Login.
- Pairing.
- Request creation.
- Classification endpoints.
- Reputation unknown queries.
- Policy mutation.

Child devices should batch non-urgent telemetry.

---

# 14. App and Domain Reputation System

## 14.1 App reputation

Backend app record:

```text
platform_app_id
platform
name
category
risk_tags
age_guidance
known_domains
reputation_confidence
last_reviewed_at
source_version
```

Sources can include public app-store metadata, curated safety datasets, Guardian classification, and parent feedback where legally/technically appropriate.

Do not scrape private child accounts.

## 14.2 Domain reputation

Record:

```text
domain
registrable_domain
categories
risk_score
confidence
first_seen
last_seen
source_version
```

Local child bundle should contain high-value domain/category intelligence in compact structure.

## 14.3 Distribution

Do not ship a multi-gigabyte raw database to devices.

Use:

- Core blocked domain sets.
- Compact hashed/trie/Bloom structures.
- Incremental deltas.
- Device cache for resolved unknowns.
- TTL by confidence/category.

## 14.4 Unknown classification endpoint

Request:

```json
{
  "domain": "example.com",
  "public_metadata": {
    "source_app_category": "BROWSER"
  },
  "policy_context": {
    "age_band": "PRETEEN"
  }
}
```

Do not send full private URL query strings unless needed and permitted by the user/policy.

Response:

```json
{
  "categories": ["EDUCATION"],
  "risk": "LOW",
  "confidence": 0.94,
  "recommended_action": "ALLOW",
  "ttl_seconds": 604800,
  "classification_version": "domain-v12"
}
```

---

# 15. On-Device Safety Classification

## 15.1 Why on-device

Private communication signals should remain local by default.

## 15.2 Phase strategy

### Phase 1

- Normalization.
- Curated multilingual keyword/pattern rules.
- Severity escalation requiring combinations/context rather than one keyword when possible.
- URLs/domain reputation.

### Phase 2

Add a small on-device text safety model where measured accuracy justifies it.

Candidate runtime:

- TensorFlow Lite or ONNX Runtime Mobile, selected based on binary size, performance, and model tooling.

Model requirements:

- Quantized.
- Fast on mid-range Android devices.
- Multilingual priorities based on launch markets.
- Structured multi-label safety output.
- No cloud dependency.

### Phase 3

- Calibrate thresholds by age band.
- False-positive test suite.
- Battery/performance profile.

## 15.3 Languages

Initial classifier text handling should at minimum be Unicode-safe and support English plus a configurable multilingual pattern set. Given likely initial markets, prioritize English, Hindi, Telugu, Arabic, and other target languages based on launch plan. Do not delay the core product for perfect language coverage.

## 15.4 Safety event confidence

Avoid displaying values like `97.348%` to parents.

Map internal confidence to:

- Low confidence.
- Medium confidence.
- High confidence.

Critical alert requires both sufficient severity and confidence/rule evidence.

---

# 16. API Contract Outline

All APIs versioned under `/v1` initially.

## 16.1 Parent APIs

```text
POST   /v1/auth/...
GET    /v1/family
POST   /v1/children
PATCH  /v1/children/{id}
POST   /v1/children/{id}/pairing
GET    /v1/children/{id}/summary
GET    /v1/children/{id}/activity
GET    /v1/children/{id}/policy
PUT    /v1/children/{id}/policy
GET    /v1/requests
POST   /v1/requests/{id}/resolve
GET    /v1/devices
POST   /v1/devices/{id}/revoke
```

## 16.2 Child-device APIs

```text
POST   /v1/device/pair
POST   /v1/device/heartbeat
GET    /v1/device/policy
POST   /v1/device/policy/applied
POST   /v1/device/events/batch
POST   /v1/device/requests
GET    /v1/device/requests/{id}
POST   /v1/reputation/domain/check
POST   /v1/reputation/app/check
```

## 16.3 Idempotency

Use idempotency keys for:

- Pair completion.
- Request creation.
- Request resolution.
- Policy mutations.
- Event batches.

## 16.4 Error model

```json
{
  "error": {
    "code": "POLICY_VERSION_CONFLICT",
    "message": "Policy changed on another device.",
    "retryable": true,
    "details": {}
  }
}
```

No stack traces to clients.

---

# 17. Shared React Native Architecture

## 17.1 Baseline

Use:

- Latest stable Expo SDK at implementation start; as of this PRD, Expo SDK 56 is a suitable baseline if stable in the repository environment.
- React Native New Architecture enabled.
- Expo Router.
- TypeScript strict mode.
- Expo Development Builds (`expo-dev-client`).
- Local Expo Modules for Guardian native bridge.

Pin versions in lockfile. Do not chase nightly versions during the three build phases.

## 17.2 Why not Expo Go

Expo Go only contains native code included in its fixed runtime. Guardian requires custom native Kotlin/Swift, Android services, iOS app extensions, entitlements, and Network Extension/Screen Time integration.

## 17.3 State management

Prefer a small, explicit state stack:

- Server state: TanStack Query or equivalent.
- Local UI state: React hooks/context or a lightweight store.
- Avoid heavyweight global state architecture unless real complexity requires it.

Native protection truth remains native and is exposed as summarized state/events.

## 17.4 Shared domain types

```text
packages/contracts/
  child.ts
  policy.ts
  request.ts
  event.ts
  protection.ts
  capability.ts
```

Mirror canonical schemas in backend and native layers through generated JSON Schema/OpenAPI where practical.

## 17.5 Offline UI

Parent device:

- Show last known child state with timestamp.
- Queue safe policy edits locally then sync, but clearly show `Pending sync`.
- Never imply a rule is active until child device acknowledges applied policy.

Child device:

- Operates on local active policy.
- Requests queue when offline if meaningful, but an offline request cannot magically unlock blocked content until approval reaches device.

---

# 18. Repository Structure

Recommended monorepo:

```text
guardian/
├── apps/
│   └── mobile/
│       ├── app/                         # Expo Router screens
│       ├── src/
│       │   ├── components/
│       │   ├── design-system/
│       │   ├── features/
│       │   ├── api/
│       │   ├── state/
│       │   ├── analytics/
│       │   └── platform/
│       ├── modules/
│       │   └── guardian-protection/     # local Expo module bridge
│       ├── android/                     # committed native project
│       └── ios/                         # committed Xcode project + extensions
│
├── backend/
│   ├── app/
│   ├── migrations/
│   └── tests/
│
├── packages/
│   ├── contracts/
│   ├── policy-schema/
│   ├── design-tokens/
│   └── test-fixtures/
│
├── docs/
│   ├── architecture/
│   ├── platform/
│   ├── privacy/
│   └── release/
│
└── scripts/
```

## 18.1 Android native package structure

```text
com.guardian.app.protection/
  vpn/
  dns/
  flow/
  usage/
  accessibility/
  notifications/
  inventory/
  policy/
  health/
  sync/
  storage/
```

## 18.2 iOS native structure

```text
GuardianNative/
  FamilyControls/
  ManagedSettings/
  DeviceActivity/
  NetworkFilter/
  Policy/
  Health/
  Storage/

Extensions/
  DeviceActivityMonitor/
  ShieldConfiguration/
  ShieldAction/
  FilterData/
  FilterControl/
  DeviceActivityReport/
```

---

# 19. Native Bridge Event Contract

Events native -> React Native:

```ts
type GuardianNativeEvent =
  | { type: 'PROTECTION_STATUS_CHANGED'; status: ProtectionStatus }
  | { type: 'APP_BLOCKED'; appRef: string; reasonCode: string }
  | { type: 'WEB_BLOCKED'; domain?: string; category?: string; reasonCode: string }
  | { type: 'TIME_WARNING'; targetRef: string; remainingSeconds: number }
  | { type: 'TIME_EXPIRED'; targetRef: string }
  | { type: 'SAFETY_EVENT'; category: string; severity: string }
  | { type: 'POLICY_APPLIED'; version: number }
  | { type: 'PERMISSION_STATE_CHANGED'; capability: string; state: string };
```

Events are low-volume semantic events. Never emit raw packet streams, complete Accessibility trees, or every notification to JS.

---

# 20. Privacy and Security Requirements

## 20.1 Data classes

### Class A - Parent account data

- Email.
- Authentication.
- Family role.

### Class B - Child profile data

- Name/display name.
- Age/age band.
- Device mapping.

### Class C - Usage metadata

- App/category durations.
- Schedule events.
- Device health.

### Class D - Safety metadata

- Category.
- Severity.
- Source app reference.
- Domain category.
- Timestamp.

### Class E - Raw private content

- Notification text.
- Visible UI text.
- Message text.
- Network payload.

**Class E is local/ephemeral by default and must not be uploaded or persisted.**

## 20.2 Data minimization

- Do not collect device location.
- Do not collect contacts.
- Do not collect microphone/camera data except QR scanning during pairing.
- Camera permission for QR scanning is used interactively only.
- Do not collect persistent hardware identifiers.
- Do not collect browsing query strings unless a specific feature requires them and policy/consent permits.

## 20.3 Encryption

- TLS 1.2+; prefer TLS 1.3.
- Encrypt databases/storage at provider/platform level.
- Device secrets in Keystore/Keychain.
- Signed policy bundles.
- Rotate backend secrets.
- Never log access tokens.

## 20.4 Authorization

Every backend read/write must enforce:

```text
parent -> family membership -> child ownership/access
```

Child device credential can only:

- Read its own policy.
- Send its own minimized events/health.
- Create requests for its child profile.
- Receive resolutions for its requests.

It cannot read parent details or other children.

## 20.5 Local child database

Encrypt or protect sensitive state using platform-supported storage and secure keys.

No private raw-content logs.

## 20.6 Audit trail

Record important control changes:

- Policy changed.
- Parent approval.
- Device paired/revoked.
- Protection permission lost/restored.

Avoid logging the private content that caused an event.

## 20.7 Deletion

Parent can:

- Delete activity history.
- Delete child profile.
- Revoke device.
- Delete account/family.

Deletion jobs must propagate to analytics/event stores, subject to legally required minimal security/audit retention.

## 20.8 Child privacy and regulatory posture

Before production launch, legal/privacy review must cover applicable child-privacy regimes for target markets, including parental consent and child-data requirements. At minimum evaluate:

- US COPPA requirements.
- EU GDPR child-data requirements.
- UK child-design/privacy requirements.
- India DPDP framework and applicable child-data rules.
- Google Play Families/user-data/monitoring policies.
- Apple App Store child safety/privacy requirements.

This PRD is not legal certification.

## 20.9 Monitoring/stalkerware compliance - Android

Guardian must be visibly marketed and operated as parental control.

Use Google Play monitoring-tool metadata where required for child monitoring and comply with visible-notification/disclosure requirements.

No hidden app icon or stealth mode.

---

# 21. Performance and Reliability Budgets

## 21.1 Native hot path

Targets:

- App policy lookup p95: <5 ms.
- Cached domain policy lookup p95: <10 ms.
- Compiled schedule lookup p95: <2 ms.
- Android visible app-block response p95: <500 ms after detectable app foreground event.
- iOS shields should be applied before blocked activity is meaningfully accessible where DeviceActivity/ManagedSettings semantics permit.

## 21.2 Cloud

- API p95 for ordinary authenticated reads: <500 ms in launch regions.
- Policy update server processing: <500 ms excluding push delivery.
- Unknown-domain classifier p95 target: <2 seconds; local policy determines what happens while waiting.

## 21.3 Battery

Measure on physical devices:

- 8-hour idle.
- 4-hour mixed Wi-Fi/mobile data.
- Video streaming.
- Gaming.
- High-notification chat day.

Targets:

- <5% incremental daily battery overhead typical.
- No continuous high-frequency Accessibility traversal.
- Batch event upload.
- Avoid wake locks except necessary short work.

## 21.4 Memory

Do not load unbounded domain lists as string objects.

Use compact data structures.

Extensions on iOS have strict memory constraints; profile each extension independently.

## 21.5 Network overhead

Guardian cloud telemetry should be tiny relative to child traffic.

Do not send packet payloads.

Batch non-urgent telemetry.

---

# 22. Analytics and Observability

## 22.1 Product analytics

Allowed analytics should focus on Guardian product behavior, not monetizing child activity.

Examples:

- Onboarding step completion.
- Permission grant/denial.
- Policy screen usage.
- Request approval latency.
- Protection health uptime.
- Feature error rate.

Do not send raw child notification/message data to analytics providers.

## 22.2 Operational telemetry

Track:

- VPN service crashes/restarts.
- Policy compile failures.
- Extension crashes.
- DeviceActivity scheduling failures.
- WebSocket disconnect rate.
- Push delivery acknowledgment where available.
- Backend error rate.

## 22.3 Privacy-conscious crash reporting

Scrub:

- Domains when unnecessary.
- Child names.
- Notification text.
- URLs/query strings.
- Tokens.

---

# 23. Store and Platform Policy Requirements

## 23.1 Google Play

Before release:

- VpnService declaration.
- Prominent disclosure and consent for sensitive data/APIs.
- Accessibility declaration and precise use description if Accessibility is included.
- Notification access disclosure.
- Monitoring-tool `isMonitoringTool` child-monitoring metadata if applicable/currently required.
- Data Safety form.
- Privacy policy in app and Play Console.
- Package visibility review; avoid QUERY_ALL_PACKAGES unless truly required and approved.
- Families/minor-data review as applicable.

## 23.2 Apple App Store

Before release:

- Family Controls distribution entitlement for host app and relevant Screen Time extensions.
- Network Extension entitlements/configuration.
- Accurate privacy nutrition labels.
- Family/child authorization behavior tested on real Family Sharing accounts.
- No private API.
- No attempt to access arbitrary third-party notification databases.
- App Review notes clearly explain parental-control use and setup.

## 23.3 Entitlement risk is a release dependency

Apple entitlement requests should be initiated at the start of Phase 1, not after engineering is complete.

---

# 24. Three-Phase Build Plan

The product must be built in three phases. Each phase is a vertical slice and must leave the repository compiling.

## Phase 1 - Core Guardian: Identity, Design System, App/Time/Web Enforcement

### Goal

Create the real consumer product foundation and prove platform-native enforcement on physical Android and iOS devices.

### Shared/mobile deliverables

- Upgrade/migrate prototype to current stable Expo Development Build workflow.
- Commit native Android/iOS projects.
- Implement Guardian Design System tokens/components.
- Parent/Child role selection.
- Auth/family/child profile.
- Pairing QR/code.
- Age bands and recommended policy defaults.
- Parent Home.
- Child Home/My Time.
- Rules navigation.
- Requests data model/basic flow.
- Protection Health screen.
- Quick Control/Search baseline.
- Phone + tablet adaptive shells.

### Backend deliverables

- Auth/family/child/device models.
- Pairing.
- Device auth.
- Versioned policy service.
- Signed policy bundle.
- Realtime/push skeleton.
- Health/heartbeat.
- Request service.
- Basic event ingestion.

### Android deliverables

- GuardianProtection Expo Module.
- VpnService with production-capable forwarding baseline.
- DNS/domain blocking local policy.
- UsageStats integration.
- LauncherApps inventory.
- Package change monitoring.
- Accessibility foreground observer and block overlay.
- App daily limits.
- Basic routines/bedtime.
- Protection permission setup.
- Local policy store/evaluator.
- Health detection.

### iOS deliverables

- Family Controls entitlement development setup/request distribution entitlement.
- Child authorization flow.
- Managed Settings app/category/domain shield baseline.
- Device Activity Monitor extension.
- Basic daily limits and scheduled routine enforcement.
- Shield Configuration + Shield Action extensions.
- Network Extension content filter baseline.
- Filter Data + Filter Control extensions.
- Local signed policy snapshot.
- Health detection.

### Phase 1 exit criteria

On physical devices:

1. Parent creates child and pairs Android/iPhone.
2. Parent sets age-based policy.
3. Child reaches blocked domain -> blocked locally.
4. Parent sets app time limit -> enforcement activates after threshold.
5. Parent changes rule -> online child applies new signed policy.
6. Child can request more time -> parent can approve -> child resumes.
7. Permission/filter disable produces health warning.
8. App works on at least one phone and one tablet form factor per platform.

No fake simulation is accepted for exit.

---

## Phase 2 - Intelligence: Communication Safety, Reputation, Rich Requests, Activity

### Goal

Turn Guardian from controls into an intelligent digital-safety layer without making cloud AI the hot path.

### Shared/mobile deliverables

- Full Requests inbox.
- Push actions.
- Rich Activity dashboard.
- Web block history/category summary.
- App controls polish.
- New app review UX.
- Communication Safety settings.
- Safety Event detail UX.
- Better Quick Control commands.
- Age-adaptive copy/detail density.

### Backend deliverables

- Domain reputation service.
- App reputation service.
- Unknown-domain classification.
- Incremental reputation bundle/deltas.
- Safety event pipeline.
- Usage aggregation.
- Reports.
- Parent notification severity/routing.

### Android deliverables

- NotificationListenerService.
- Local communication risk patterns.
- On-device lightweight text classifier if accuracy/performance spike passes.
- Optional Accessibility visible-text risk signals.
- Domain/app/source correlation.
- VPN/proxy/bypass risk categories.
- More resilient block overlay/tamper health.
- Session budgets/cooldowns if desired.

### iOS deliverables

- Rich NetworkExtension flow attribution using source app metadata where available.
- Domain/category reputation integration.
- iOS 26+ URL Filter spike and implementation if entitlement/API practical.
- Device Activity reports/local summary surfaces.
- Communication Risk Signals UI explicitly reflecting iOS capability ceiling.
- Improved Managed Settings category/app targeting.

### Phase 2 exit criteria

1. Known risky domain classification is instant/local after bundle sync.
2. Unknown domain can be classified and cached without sending raw child traffic.
3. Android risky notification preview can produce local minimized safety event without persisting raw message.
4. iOS UI accurately states unavailable message-inspection capability while still showing network/app risk signals.
5. Parent receives actionable request/safety notifications.
6. Activity view shows useful summaries with platform-appropriate data.
7. False-positive safety events can be reported.

---

## Phase 3 - Ship: Polish, Hardening, Accessibility, Performance, Store Readiness

### Goal

Convert the beta into a reliable App Store/Play Store product without adding a large new feature family.

### Design/UX

- Full Apple HIG review.
- iOS 26+/current Liquid Glass adoption for system navigation/control layers.
- Android edge-to-edge/predictive back review.
- Tablet split-view review.
- Dark mode.
- Dynamic Type/large text.
- TalkBack/VoiceOver.
- RTL.
- Reduce Motion/Transparency.
- Copy pass for all age bands.
- Verify 3-Interaction Law on every feature.

### Security/privacy

- Threat model.
- Authz tests.
- Device key rotation/revocation.
- Signed-policy validation/fuzz tests.
- Local raw-content non-retention tests.
- Log redaction.
- Privacy export/deletion.
- Rate limits.
- Dependency audit.

### Reliability/performance

- Android VPN soak tests.
- Battery benchmarks.
- DNS/IPv6/QUIC testing.
- Offline tests.
- Reboot/service recovery.
- iOS extension memory tests.
- DeviceActivity schedule/timezone tests.
- Large domain bundle performance.
- Push/realtime fallback tests.

### Store readiness

- Google declarations/disclosures.
- Accessibility/VPN review package.
- Monitoring-tool policy compliance.
- Apple entitlement approval/verification.
- App Review notes.
- Privacy policy/Data Safety/App Privacy.
- Production signing.
- TestFlight/Internal testing.

### Phase 3 exit criteria

- All P0/P1 acceptance tests pass.
- No known raw child-content leakage.
- No blocker store-policy issue.
- Core features pass on supported OS matrix.
- Protection-health accuracy validated.
- Crash-free beta target met over meaningful test cohort.
- Battery target within acceptable range.
- Every primary feature has platform-correct empty/loading/error/offline states.
- No placeholder or simulation remains in production paths.

---

# 25. Priorities

## P0 - Must ship

- One-app Parent/Child role.
- Pairing.
- Age bands.
- App controls.
- Daily limits.
- Bedtime/routines.
- Web/domain filtering.
- Local policy engine.
- Android VPN.
- Android Usage Access.
- Android app-block Accessibility layer.
- iOS Family Controls.
- iOS Managed Settings.
- iOS Device Activity.
- iOS content filter.
- Requests/approvals.
- Protection health.
- Parent/child Home.
- Offline policy.
- Privacy/security basics.

## P1 - Strong launch value

- Android Notification Communication Safety.
- Domain/app reputation.
- Unknown classification.
- Activity summaries.
- New app alerts.
- On-device text safety classifier.
- Rich quick controls.
- iOS flow attribution.
- iOS 26 URL filtering where feasible.

## P2 - After launch unless trivial

- Advanced session cooldowns.
- Highly customized natural-language parent intent.
- Extensive weekly insights.
- Advanced child self-management goals.
- Multi-language UX beyond launch languages.

Do not let P2 delay P0/P1.

---

# 26. Screen Inventory

## Parent phone

1. Welcome.
2. Sign in.
3. Sign up.
4. Create/join family.
5. Add child.
6. Age/preset.
7. Pairing QR.
8. Home.
9. Child detail.
10. Activity overview.
11. Activity app/category detail.
12. Web activity.
13. Safety events.
14. Rules overview.
15. Apps list.
16. App detail/editor.
17. Screen Time.
18. Routine list.
19. Routine editor.
20. Web & Content.
21. Website/category rules.
22. Communication Safety.
23. Requests inbox.
24. Request detail.
25. Quick Control/Search.
26. Protection Health.
27. Family settings.
28. Guardian/device settings.
29. Privacy settings.
30. Notification settings.
31. Help/troubleshooting.
32. Account/subscription placeholder if monetization is added.

## Child phone

1. Welcome/child role.
2. Scan/enter code.
3. Protection setup.
4. Home.
5. My Time.
6. Requests.
7. New request.
8. Time-up/block screen.
9. Web block/remediation.
10. Protection needs attention.
11. Simple rules summary.
12. About/privacy explanation.

## Tablet

Same semantic destinations composed into split-view/adaptive layouts rather than separate product features.

---

# 27. Three-Interaction Compliance Matrix

Representative routes; QA must complete full matrix before release.

| Task | Valid path | Reach depth target |
|---|---|---:|
| Approve +15 min | Parent push action | 1 |
| Add time from app | Home -> child +15m | 2 |
| Pause child internet | Home -> child Pause | 2 |
| Open child rules | Home -> child -> Rules | 2-3 |
| Block app | Home -> Quick Control -> app -> Block | <=3 to action surface |
| Change bedtime | Home -> Quick Control -> Bedtime -> edit | <=3 to edit surface |
| View pending requests | Home -> Requests card / Requests tab | 1 |
| View protection issue | Home -> Needs attention | 1 |
| Fix child permission | Home -> Needs attention -> Fix instructions | 2 |
| Block domain | Quick Control -> domain -> Block | <=3 |
| View today's web blocks | Home -> Today web summary | 1-2 |
| Change communication safety | Home -> Rules -> Communication Safety | 2 |
| Child asks for time | Time-up -> Ask Parent -> duration | 2-3 |
| Child sees remaining time | Child Home | 0 |

QA must reject navigation structures that bury normal features beyond the invariant.

---

# 28. Edge Cases

## 28.1 Multiple child devices

One child profile can have multiple devices.

Policy applies to child profile by default. Allow device-specific override later if needed.

Usage can be:

- Per-device.
- Combined family budget, if implemented carefully.

V1 default: per-device usage enforcement to avoid cross-platform synchronization races. Parent summary can aggregate.

## 28.2 Multiple guardians change same policy

Use optimistic concurrency with policy version.

If conflict:

- Server applies latest valid mutation with version check.
- Losing client refetches.
- UI says `Updated by another guardian` rather than silently overwriting.

## 28.3 Child device offline

- Local rules continue.
- Parent new rules show `Waiting for device`.
- Temporary grants do not apply until device receives them.
- Parent sees last seen.

## 28.4 Timezone change

- Device reports timezone change.
- Scheduled policies recalculate locally.
- Prevent easy clock manipulation from resetting limits by using monotonic usage tracking and server sanity checks.

## 28.5 Reinstall

- Parent device: sign in restores family.
- Child device: re-pair unless secure device restoration safely preserves credential.
- iOS Family Controls state must be revalidated.

## 28.6 App renamed/reinstalled

- Android package ID is canonical identity.
- Version/update event refreshes metadata.
- iOS token validity checked; revocation/authorization changes invalidate as documented.

## 28.7 Shared Android UID

If multiple packages share UID and flow attribution cannot distinguish, apply the most restrictive relevant network rule or mark source ambiguous, depending on risk. Do not report false exact attribution.

## 28.8 VPN conflict

Android generally supports one active VPN service per user. Guardian must detect another VPN conflict and explain that web protection cannot operate simultaneously under normal Android VPN constraints.

Do not silently disable another VPN.

## 28.9 Apple content filter/VPN interactions

Test interaction with Private Relay/VPN/network extensions. Apple notes Network Extension providers do not use iCloud Private Relay in the same manner; Guardian must test actual behavior and surface conflicts clearly.

## 28.10 Captive portal

Web filter must permit system captive portal flows required to join Wi-Fi, with safe exceptions.

## 28.11 Emergency/system services

Do not block:

- Emergency calling.
- Critical OS connectivity required for device function.
- Guardian's own policy sync/parent request path.

---

# 29. Threat Model

## 29.1 Adversaries

- Curious child attempting casual bypass.
- Technically sophisticated teen disabling permissions.
- Malicious website.
- Malicious app.
- Network attacker.
- Compromised Guardian account.
- Compromised backend credential.

## 29.2 Major threats

### T1 - Child disables Android VPN

Mitigation:

- Health monitor.
- Parent alert.
- Persistent health status.
- Encourage user-configured Always-on VPN.
- Continue app/time controls.

Residual risk: Standard Android app cannot guarantee VPN remains enabled.

### T2 - Child disables Accessibility

Mitigation:

- Detect via secure settings/accessibility manager state.
- Parent alert.
- Child health prompt.
- Network blocking remains.

Residual risk: Strong visual app blocking degraded.

### T3 - Child uninstalls Android app

Mitigation:

- Best-effort Accessibility tamper guard when enabled.
- Parent loses heartbeat -> immediate/meaningful alert.

Residual risk: No Device Owner means uninstall cannot be guaranteed impossible.

### T4 - Policy tampering on device

Mitigation:

- Signed policy bundles.
- Secure local storage.
- App sandbox.

### T5 - Parent account takeover

Mitigation:

- Strong auth.
- Rate limits.
- Session/device controls.
- Optional MFA/passkey after core launch.
- Notify existing guardians of security-sensitive changes.

### T6 - Raw child content leaks to logs

Mitigation:

- Never log raw content.
- Typed logging wrappers.
- Automated log-redaction tests.
- Crash-report scrubber.

### T7 - Classifier false positive

Mitigation:

- Confidence threshold.
- Parent review.
- Allowlist.
- Feedback.
- Avoid one-keyword critical alerts.

### T8 - Malicious policy bundle injection

Mitigation:

- Signature verification.
- Version monotonicity.
- TLS.

### T9 - Malicious/compromised domain intelligence

Mitigation:

- Signed bundles.
- Dataset provenance.
- Rollback.
- Independent hard-block list review.

---

# 30. Testing Strategy

## 30.1 Unit tests

- Policy precedence.
- Schedule evaluation.
- Age defaults.
- Temporary overrides.
- Time rollover.
- Domain normalization.
- Domain matching.
- Classifier schema.
- Request state machine.
- Policy signature verification.

## 30.2 Android instrumentation

- VPN start/stop.
- DNS block.
- IPv4/IPv6.
- Usage events.
- Accessibility block overlay.
- Notification listener classification.
- Permission revocation.
- Reboot recovery.
- App install event.

## 30.3 iOS tests

Physical device required for major Screen Time/Network Extension validation.

Test:

- Child authorization.
- App shield.
- Category shield.
- Web domain shield.
- Device Activity threshold.
- Scheduled routine.
- Shield action request.
- Content filter allow/block.
- Source app metadata availability.
- iOS 26 URL filter conditional path.
- Entitlement/release provisioning.

## 30.4 Cross-platform acceptance families

Test ages:

- 7.
- 11.
- 14.
- 17.

Test device classes:

- Budget/mid Android phone.
- Current Android phone.
- Android tablet.
- Current iPhone.
- Older supported iPhone.
- iPad.

## 30.5 Network scenarios

- Wi-Fi.
- Mobile data.
- Network switch mid-session.
- No network.
- Captive portal.
- IPv6-only/dual stack where available.
- QUIC-heavy streaming.
- DNS over HTTPS app/service attempts.
- Another VPN installed/active.

## 30.6 Accessibility QA

- VoiceOver.
- TalkBack.
- Largest text sizes.
- Reduced motion.
- High contrast.
- RTL.
- Tablet keyboard where supported.

## 30.7 3-Interaction automated/manual audit

Maintain a route manifest with each feature and shortest path from Home.

CI can detect route-depth regressions for declarative route metadata; manual UX review validates actual deliberate interactions.

---

# 31. UI States Required for Every Data Surface

Every significant screen/component must define:

- Initial.
- Loading.
- Loaded.
- Empty.
- Offline.
- Stale.
- Permission denied.
- Platform unavailable.
- Error/retry.
- Pending sync.

Example App Activity on iOS when detailed export unavailable:

```text
Detailed app activity isn't available in this view on this iPhone.
Guardian can still enforce the app limits and show the protection activity it records.
```

Not:

```text
0 minutes
```

if zero is not actually known.

---

# 32. Product Copy and Safety Language

## 32.1 Parent safety alert

Preferred:

> Guardian detected a high-risk self-harm signal in a notification on Emma's Android device. The message text was analyzed on the device and wasn't stored. Consider checking in with Emma.

Only show this wording if the signal truly came from notification analysis.

## 32.2 iOS limitation

Preferred:

> iPhone protects app use and web access, but iOS doesn't let Guardian read messages or notifications from other apps.

This should be available in feature info before the parent expects Android-equivalent communication inspection.

## 32.3 Child block copy by age

Young Child:

> This app is taking a break right now. You can ask your parent if you need more time.

Preteen:

> You've reached today's YouTube limit. Ask for more time if you need it.

Teen:

> Today's YouTube limit is finished. You can request an extension.

Older Teen:

> Your family limit for YouTube is reached for today. Request more time or check your schedule.

---

# 33. Subscription/Monetization Architecture

Pricing is intentionally not specified in this PRD.

Engineering requirement:

- Core policy engine must not be entangled with billing SDK.
- Family has entitlement flags.
- Feature gating occurs at configuration/UI edge, not inside packet hot path.
- Safety-critical existing rules must not suddenly fail open because a billing refresh is unavailable.

Possible entitlement model:

```text
FREE_OR_TRIAL
PREMIUM
GRANDFATHERED
PAST_DUE_GRACE
EXPIRED
```

Do not implement until product owner supplies pricing unless a placeholder entitlement schema is needed.

---

# 34. Migration from Existing YouTube Prototype

The existing prototype contains useful pieces:

- Parent/child pairing.
- FastAPI.
- Supabase/Postgres.
- WebSocket bridge.
- Child profiles.
- Parent block intent.
- Pattern + AI classifier structure.
- Parent decisions.
- Alerts/history.

Keep/reuse concepts where clean, but do not preserve the WebView-centric architecture as the product core.

### Deprecate as core

```text
YouTube WebView
Injected click JS
Per-video WebView navigation interception
```

### Reframe

The YouTube prototype becomes an optional future content adapter/lab for public content IDs, not the universal enforcement foundation.

### Security cleanup before reuse

Remove demo fallback credentials, open CORS, and permissive database policies from any production path. Enforce tenant/family ownership in backend and database policies.

---

# 35. Engineering Decision Log

## ED-001 - One app, two roles

**Decision:** One mobile app/binary with parent and child device roles.

**Reason:** Less duplicated UI/backend/auth/release work; coherent brand; easier pairing/deep links; shared design system.

## ED-002 - Expo Development Build, not Expo Go

**Decision:** Use Expo tooling + committed native projects + custom native modules/extensions.

**Reason:** Fast UI iteration plus full native control.

## ED-003 - No fully native duplicate apps

**Decision:** Do not build separate Compose and SwiftUI apps end-to-end.

**Reason:** Duplicates product work without improving hot-path enforcement.

## ED-004 - Native enforcement

**Decision:** Kotlin/Swift own policy enforcement and OS integration.

**Reason:** Performance, reliability, background execution, extension constraints.

## ED-005 - No enterprise management

**Decision:** Standard consumer installation only.

**Tradeoff:** Android app-block/tamper resistance is best-effort rather than absolute.

## ED-006 - No location

**Decision:** Focus product and permissions on digital safety/time.

## ED-007 - No TLS MITM

**Decision:** Domain/URL/OS metadata and public-content intelligence only.

**Reason:** Security, privacy, maintainability, app compatibility, trust.

## ED-008 - Raw private communication local-only

**Decision:** Analyze Android notification/Accessibility text locally, persist minimized safety event only.

## ED-009 - Apple HIG as primary design authority

**Decision:** Guardian follows Apple's design principles and system components heavily on iOS; Android preserves the same design DNA while using Android-native interaction conventions.

## ED-010 - Atlassian typography inspiration

**Decision:** Use Apple's system typography on Apple platforms; use Inter Variable or a similarly legible typeface on Android, borrowing Atlassian's legibility/hierarchy philosophy without shipping Atlassian's proprietary fonts.

## ED-011 - Three phases

**Decision:** Core, Intelligence, Ship. No separate fourth hardening phase.

---

# 36. Open Technical Spikes - Resolve Early, Do Not Turn Into Product Questions

These are engineering validations, not reasons to block the build.

## Spike A - Android VPN forwarding core

Compare production-ready licensed options versus internal implementation for TUN -> socket forwarding. Choose fastest reliable option with IPv6/QUIC support.

## Spike B - Android app-block overlay reliability

Validate Accessibility overlay + app transition detection across Samsung, Pixel, Xiaomi/HyperOS, OnePlus/Oppo families.

## Spike C - Android Play review package

Validate Accessibility + NotificationListener + VpnService disclosures/declarations against current Play policies before public rollout.

## Spike D - iOS Family Controls entitlement

Request distribution entitlement immediately. Build with development entitlement while review proceeds.

## Spike E - iOS Network Extension content filter

Validate child Family Sharing authorization + content filter enablement on minimum supported iOS and current iOS.

## Spike F - iOS 26 URL Filter

Prototype full-URL block database and determine entitlement/PIR/server operational complexity. If it threatens delivery, keep it Phase 2 conditional and ship content filter/domain protection first.

## Spike G - iOS cross-device activity reporting

Validate exactly what usage aggregates Guardian can lawfully and technically synchronize to the parent app globally. Do not rely on EU-only `approvedWithDataAccess` for core.

## Spike H - On-device classifier

Benchmark a small multilingual text model on mid-range Android. Only include if it beats deterministic-only accuracy enough to justify binary/battery cost.

---

# 37. Definition of Done - Product

Guardian V1 is done when a real family can:

1. Install the same Guardian app on a parent and child device.
2. Choose roles and pair securely.
3. Configure a child age and receive age-appropriate recommended rules.
4. Enforce app time limits.
5. Enforce bedtime/school/focus rules.
6. Block unsafe web destinations device-wide to the extent supported by the OS.
7. Add custom allow/block rules.
8. Receive and resolve child access/time requests.
9. See accurate protection health.
10. Continue enforcing cached policies offline.
11. Receive Android communication-safety risk signals when relevant permissions are enabled.
12. Understand the iOS communication-safety limitation without misleading claims.
13. Use the product on phone and tablet layouts.
14. Reach every normal feature within the Guardian 3-Interaction Law.
15. Use the product with VoiceOver/TalkBack and large text.
16. Run without routing all child internet traffic through Guardian cloud.
17. Run without TLS interception.
18. Demonstrate no default cloud persistence of raw child notification/message/UI text.
19. Pass store-policy/entitlement requirements.
20. Ship stable production builds.

---

# 38. Acceptance Criteria by Core Capability

## AC-APP-01

Given an Android child app has exceeded a configured daily limit and required protection permissions are active, opening that app causes Guardian's block surface to appear within the performance target and network access is denied according to policy.

## AC-APP-02

Given an iOS app/category is shielded by policy, the system shield prevents normal access according to Managed Settings behavior.

## AC-TIME-01

Daily usage does not reset incorrectly when the device clock is manually changed backward.

## AC-TIME-02

A +15 minute grant expires automatically and restores the prior rule.

## AC-WEB-01

Known blocked domain is denied with no cloud dependency.

## AC-WEB-02

Unknown classification failure does not crash the network service; fallback follows age policy.

## AC-WEB-03

Guardian does not install a root CA.

## AC-REQ-01

Duplicate approval messages do not double-extend a time grant.

## AC-HEALTH-01

Removing Android VPN permission causes parent health state to update after configured debounce.

## AC-HEALTH-02

Revoking iOS Family Controls authorization is not shown as healthy.

## AC-PRIV-01

Automated test posts a notification containing a unique secret string. After local risk classification, that string must not appear in backend payloads, app logs, analytics, crash logs, or persistent local event database.

## AC-IOS-CEILING-01

No iOS screen claims arbitrary third-party message text is monitored.

## AC-UX-01

Every feature in the route inventory has a documented path satisfying the Guardian 3-Interaction Law.

---

# 39. Official Technical and Design References

Engineering must re-check the latest versions at implementation time because platform APIs and store policy evolve.

## Apple - Design

- Human Interface Guidelines: https://developer.apple.com/design/human-interface-guidelines/
- Design Principles: https://developer.apple.com/design/human-interface-guidelines/design-principles
- Accessibility: https://developer.apple.com/design/human-interface-guidelines/accessibility
- Typography: https://developer.apple.com/design/human-interface-guidelines/typography
- Liquid Glass overview: https://developer.apple.com/documentation/technologyoverviews/liquid-glass
- SF Symbols: https://developer.apple.com/sf-symbols/

## Apple - Parental Controls / Screen Time

- Screen Time Technology Frameworks: https://developer.apple.com/documentation/screentimeapidocumentation
- Family Controls: https://developer.apple.com/documentation/familycontrols
- Configuring Family Controls: https://developer.apple.com/documentation/xcode/configuring-family-controls
- Requesting Family Controls entitlement: https://developer.apple.com/documentation/familycontrols/requesting-the-family-controls-entitlement
- Managed Settings / Shield Settings: https://developer.apple.com/documentation/managedsettings/shieldsettings
- Device Activity: https://developer.apple.com/documentation/deviceactivity
- Network Extension content filter providers: https://developer.apple.com/documentation/networkextension/content-filter-providers
- Network Extension provider deployment TN3134: https://developer.apple.com/documentation/technotes/tn3134-network-extension-provider-deployment
- NEFilterFlow source app identifier: https://developer.apple.com/documentation/networkextension/nefilterflow/sourceappidentifier
- URL filters (iOS 26+): https://developer.apple.com/documentation/networkextension/url-filters
- FamilyActivityData: https://developer.apple.com/documentation/familycontrols/familyactivitydata
- Family Controls App and Website Usage entitlement: https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.family-controls.app-and-website-usage
- Apple child/age-appropriate experiences: https://developer.apple.com/kids/

## Apple - Notifications limitation reference

- UNNotificationServiceExtension: https://developer.apple.com/documentation/usernotifications/unnotificationserviceextension

Apple's documentation describes service extensions processing remote notifications for the app containing that extension; Guardian has no public general-purpose cross-app notification reader on iOS.

## Android - Core APIs

- VpnService: https://developer.android.com/reference/android/net/VpnService
- Android VPN developer guide: https://developer.android.com/develop/connectivity/vpn
- UsageStatsManager: https://developer.android.com/reference/android/app/usage/UsageStatsManager
- UsageEvents: https://developer.android.com/reference/android/app/usage/UsageEvents
- NotificationListenerService: https://developer.android.com/reference/android/service/notification/NotificationListenerService
- AccessibilityService guide: https://developer.android.com/guide/topics/ui/accessibility/service
- LauncherApps: https://developer.android.com/reference/android/content/pm/LauncherApps
- ConnectivityManager: https://developer.android.com/reference/android/net/ConnectivityManager
- MediaProjection (not core Guardian architecture): https://developer.android.com/media/platform/av-capture

## Google Play policy

- Permissions and APIs that Access Sensitive Information: https://support.google.com/googleplay/android-developer/answer/16558241
- VpnService policy: https://support.google.com/googleplay/android-developer/answer/12564964
- Broad package visibility policy: https://support.google.com/googleplay/android-developer/answer/10158779
- Prominent disclosure and consent: https://support.google.com/googleplay/android-developer/answer/11150561
- Monitoring tool flag: https://support.google.com/googleplay/android-developer/answer/12955211
- Google Play Families policies: https://support.google.com/googleplay/android-developer/answer/9893335

## Expo / React Native

- Expo custom native code: https://docs.expo.dev/workflow/customizing/
- Expo Development Builds: https://docs.expo.dev/develop/development-builds/introduction/
- Expo Modules API: https://docs.expo.dev/modules/overview/
- Expo iOS App Extensions: https://docs.expo.dev/build-reference/app-extensions/
- Expo config plugins/native module tutorial: https://docs.expo.dev/modules/config-plugin-and-native-module-tutorial/
- React Native New Architecture: https://reactnative.dev/architecture/landing-page

## Atlassian Design inspiration

- Typography overview: https://atlassian.design/foundations/typography/
- Product typefaces and scale: https://atlassian.design/foundations/typography/product-typefaces-and-scale

Guardian uses these as typographic inspiration; it does not redistribute Atlassian Sans or Atlassian Mono unless separately licensed.

---

# 40. Final Product Thesis

Guardian is not an app blacklist.

Guardian is not a YouTube wrapper.

Guardian is not an enterprise MDM product.

Guardian is not covert monitoring software.

Guardian is a **local-first family digital-safety layer** that combines:

```text
OS app controls
+ screen-time policy
+ device-wide network filtering
+ source-app metadata
+ domain/app reputation
+ age-adaptive rules
+ Android local communication-risk signals
+ parent approvals
+ privacy-preserving reporting
```

The architectural rule is simple:

> Enforce at the closest reliable OS boundary, classify locally when private content is involved, use cloud intelligence only for unknown/public information, and expose a calm Apple-quality family experience on top.

The product must ship quickly, but speed is achieved by narrowing architecture - one shared app, a modular backend, native enforcement engines, three phases - not by pretending platform restrictions do not exist.

**End of Master PRD.**
