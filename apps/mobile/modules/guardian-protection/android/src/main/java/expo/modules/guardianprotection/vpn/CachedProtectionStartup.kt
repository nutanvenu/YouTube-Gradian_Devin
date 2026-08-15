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
