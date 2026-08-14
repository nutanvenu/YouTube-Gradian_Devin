package expo.modules.guardianprotection.vpn

import android.content.Context

internal object GuardianVpnPreferences {
  private const val NAME = "guardian_protection"
  private const val ENABLED = "vpn_enabled"

  fun setEnabled(context: Context, enabled: Boolean) {
    context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
      .edit()
      .putBoolean(ENABLED, enabled)
      .apply()
  }

  fun isEnabled(context: Context): Boolean =
    context.getSharedPreferences(NAME, Context.MODE_PRIVATE).getBoolean(ENABLED, false)
}
