package expo.modules.guardianprotection.vpn

import android.content.Context

internal object GuardianVpnPreferences {
  private const val NAME = "guardian_protection"
  private const val ENABLED = "vpn_enabled"
  private const val ENABLE_REQUESTED = "vpn_enable_requested"

  fun setEnabled(context: Context, enabled: Boolean) {
    context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
      .edit()
      .putBoolean(ENABLED, enabled)
      .apply()
  }

  fun isEnabled(context: Context): Boolean =
    context.getSharedPreferences(NAME, Context.MODE_PRIVATE).getBoolean(ENABLED, false)

  fun setEnableRequested(context: Context, requested: Boolean) {
    context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
      .edit()
      .putBoolean(ENABLE_REQUESTED, requested)
      .apply()
  }

  fun consumeEnableRequested(context: Context): Boolean {
    val preferences = context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
    val requested = preferences.getBoolean(ENABLE_REQUESTED, false)
    if (requested) preferences.edit().remove(ENABLE_REQUESTED).apply()
    return requested
  }
}
