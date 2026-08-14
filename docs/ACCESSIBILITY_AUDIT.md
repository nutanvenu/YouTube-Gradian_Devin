# Mobile accessibility audit

## Implemented safeguards

- `ScreenScaffold` exposes the page title as a native header and leaves the scroll container
  traversable, so TalkBack/VoiceOver can reach each control in order.
- `PrimaryButton`, `SecondaryButton`, `ListRow`, and `TextField` have explicit labels, roles,
  and disabled states where applicable.
- Shared controls use the design-token minimum touch target.
- Text uses token typography with React Native font scaling enabled; no screen sets a fixed
  font size or truncates text.
- Error, loading, offline, stale, and permission-recovery messages use polite accessibility live
  regions.
- The responsive layout uses flex wrapping at regular widths and relies on React Native's RTL
  layout direction rather than hard-coded left/right positioning.
- Press feedback is opacity-only; no custom motion animation is used, so reduced-motion users
  are not exposed to app-authored transitions.
- Parent and child permission-recovery surfaces name the capability and provide a recovery
  action. iOS communication safety explicitly reads `Not available on iPhone/iPad`.

## Device evidence

The accessibility node dump was captured from the development client, but the current launcher
session remained on the Expo development-menu confirmation surface, so the screenshots below are
not claimed as parent/child product-surface verification:

```text
.scratch/emulator/accessibility/parent-large-text.png
.scratch/emulator/accessibility/child-large-text.png
.scratch/emulator/accessibility/parent-rtl.png
.scratch/emulator/accessibility/child-rtl.png
.scratch/emulator/accessibility/talkback-node-check.txt
```

The shared control semantics, contrast tokens, and touch targets are source-verified against
`packages/design-tokens/src/index.ts`. A real TalkBack traversal and large-text/RTL rendering
pass on authenticated parent and child routes remains outstanding because the launcher
confirmation prevented reaching those routes in this pass. iPad Dynamic Type and native
split-view remain Mac-only verification gaps.
