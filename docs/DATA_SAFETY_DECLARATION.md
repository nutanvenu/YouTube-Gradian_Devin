# Guardian Android Data Safety declaration

This declaration is the source of truth for the Play Console Data Safety form.

## Collected and transferred

Guardian transfers the following to its first-party backend for account, family-safety,
enforcement, reporting, and notification routing:

- Account email and authentication/session records.
- Parent, family, and child names.
- Child date of birth and derived age band.
- Child timezone, device identifiers, platform, and capability/permission state.
- Policy, reputation, request, approval, and synchronization metadata.
- Usage aggregates and reports: app/category references, durations, event timestamps, and
  timezone.
- Web activity metadata: minimized domain identifiers, app references, category, and event time.
- Communication-safety metadata only when the parent opts in: category, severity, source app,
  timestamp, confidence, and reason code.
- Notification routing metadata and delivery status.

These data are used for family-safety functionality and are deleted through the in-app
account-deletion action or the authenticated `DELETE /v1/auth/account` route. The public
deletion information page is `/account-deletion`.

## Not collected or transferred

- Raw notification title or body.
- Message content, browsing URLs, URL paths, query strings, or fragments.
- Passwords, private keys, or access/refresh token values.
- Audio, music files, screenshots, or screen recordings.
- APNs/FCM provider delivery data unless a future provider integration is enabled.

Raw notification text is processed transiently in Android memory by the opt-in
`NotificationListenerService` path and discarded. It is not persisted, logged, bridged to
JavaScript, uploaded, or shown to parents.

## Local-only capability state

The Android VPN, Accessibility service, Usage Access, and notification access are
user-authorized capabilities. Their local permission state and supported/degraded level may be
included in the device heartbeat. iOS reports communication safety as unavailable where the
platform does not provide the equivalent notification-listener capability.

The declaration must be revisited if storage, analytics, crash reporting, provider delivery, or
third-party reputation integrations are added.
