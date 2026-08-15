package expo.modules.guardianprotection.vpn

internal object CachedProtectionStartup {
  fun shouldStart(
    protectionEnabled: Boolean,
    hasVerifiedSnapshot: Boolean,
    vpnConsentGranted: Boolean,
  ): Boolean = protectionEnabled && hasVerifiedSnapshot && vpnConsentGranted
}

internal object UserInitiatedProtectionStartup {
  fun shouldStart(
    hasVerifiedSnapshot: Boolean,
    vpnConsentGranted: Boolean,
  ): Boolean = hasVerifiedSnapshot && vpnConsentGranted
}

internal enum class UserInitiatedEnableIntentAction {
  KEEP,
  CONSUME,
  EXPIRE,
}

internal object UserInitiatedEnableIntent {
  const val MAX_AGE_MILLIS = 5 * 60 * 1000L

  fun action(
    recordedAt: Long?,
    now: Long,
    consentGranted: Boolean,
  ): UserInitiatedEnableIntentAction {
    if (recordedAt == null || now < recordedAt || now - recordedAt > MAX_AGE_MILLIS) {
      return UserInitiatedEnableIntentAction.EXPIRE
    }
    return if (consentGranted) {
      UserInitiatedEnableIntentAction.CONSUME
    } else {
      UserInitiatedEnableIntentAction.KEEP
    }
  }
}
