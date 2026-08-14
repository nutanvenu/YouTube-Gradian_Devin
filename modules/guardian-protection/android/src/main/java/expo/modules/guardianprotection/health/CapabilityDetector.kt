package expo.modules.guardianprotection.health

import android.app.AppOpsManager
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.net.VpnService
import android.provider.Settings
import android.os.Process
import java.time.Instant

class CapabilityDetector(private val context: Context) {
  fun getCapabilities(): Map<String, Map<String, Any?>> {
    val now = Instant.now().toString()
    return mapOf(
      "vpn_filtering" to status(if (VpnService.prepare(context) == null) "FULL" else "UNAVAILABLE", now, "VPN consent"),
      "app_usage" to status(if (usageAccessGranted()) "FULL" else "UNAVAILABLE", now, "Usage Access"),
      "accessibility_signals" to status(if (accessibilityGranted()) "FULL" else "UNAVAILABLE", now, "Accessibility"),
      "notification_signals" to status(if (notificationAccessGranted()) "FULL" else "UNAVAILABLE", now, "Notification access"),
      "app_blocking" to status("UNAVAILABLE", now, "Native evaluator is available; enforcement service is not started"),
      "web_filtering" to status("UNAVAILABLE", now, "VPN service is not started"),
      "communication_risk_signals" to status(if (notificationAccessGranted() || accessibilityGranted()) "BEST_EFFORT" else "UNAVAILABLE", now, "Signal sources"),
    )
  }

  fun requestVpnPermission(): Map<String, Any?> {
    val intent = VpnService.prepare(context)
    if (intent == null) return mapOf("granted" to true)
    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    context.startActivity(intent)
    return mapOf("granted" to false, "reason" to "VPN_CONSENT_REQUIRED")
  }

  fun openUsageAccessSettings() {
    context.startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
  }

  fun openAccessibilitySettings() {
    context.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
  }

  fun openNotificationAccessSettings() {
    context.startActivity(Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
  }

  fun observedApps(): List<Map<String, Any?>> =
    context.packageManager.getInstalledApplications(0)
      .filter { it.packageName != context.packageName }
      .map {
        mapOf(
          "platformAppId" to it.packageName,
          "displayName" to context.packageManager.getApplicationLabel(it).toString(),
          "category" to category(it),
          "observedAt" to Instant.now().toString(),
        )
      }

  private fun category(application: ApplicationInfo): String =
    if ((application.flags and ApplicationInfo.FLAG_SYSTEM) != 0) "SYSTEM" else "UNKNOWN"

  private fun usageAccessGranted(): Boolean {
    val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
    return appOps.checkOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), context.packageName) == AppOpsManager.MODE_ALLOWED
  }

  private fun accessibilityGranted(): Boolean {
    val enabled = Settings.Secure.getString(context.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES) ?: return false
    return enabled.split(':').any { it.startsWith(context.packageName) }
  }

  private fun notificationAccessGranted(): Boolean {
    val enabled = Settings.Secure.getString(context.contentResolver, "enabled_notification_listeners") ?: return false
    return enabled.split(':').any { it.startsWith(context.packageName) }
  }

  private fun status(level: String, updatedAt: String, detail: String) = mapOf(
    "level" to level,
    "detail" to detail,
    "updatedAt" to updatedAt,
  )
}
