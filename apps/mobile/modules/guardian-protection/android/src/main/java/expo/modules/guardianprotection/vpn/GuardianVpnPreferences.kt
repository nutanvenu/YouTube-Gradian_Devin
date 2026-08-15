package expo.modules.guardianprotection.vpn

import android.content.Context

internal object GuardianVpnPreferences {
  private const val NAME = "guardian_protection"
  private const val ENABLED = "vpn_enabled"
  private const val ENABLE_REQUESTED_AT = "vpn_enable_requested_at"

  fun setEnabled(context: Context, enabled: Boolean) {
    context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
      .edit()
      .putBoolean(ENABLED, enabled)
      .apply()
  }

  fun isEnabled(context: Context): Boolean =
    context.getSharedPreferences(NAME, Context.MODE_PRIVATE).getBoolean(ENABLED, false)

  fun recordEnableRequested(context: Context, recordedAt: Long = System.currentTimeMillis()) {
    context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
      .edit()
      .putLong(ENABLE_REQUESTED_AT, recordedAt)
      .apply()
  }

  fun enableRequestedAt(context: Context): Long? =
    context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
      .getLong(ENABLE_REQUESTED_AT, -1L)
      .takeIf { it >= 0L }

  fun clearEnableRequested(context: Context) {
    val preferences = context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
    preferences.edit().remove(ENABLE_REQUESTED_AT).apply()
  }
}
