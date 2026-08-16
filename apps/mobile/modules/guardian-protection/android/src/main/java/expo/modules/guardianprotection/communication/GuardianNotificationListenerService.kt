package expo.modules.guardianprotection.communication

import android.content.pm.ApplicationInfo
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import expo.modules.guardianprotection.BuildConfig
import expo.modules.guardianprotection.content.ContentSafetyServiceRuntime

class GuardianNotificationListenerService : NotificationListenerService() {
  override fun onListenerConnected() {
    super.onListenerConnected()
    ContentSafetyServiceRuntime.bootstrap(this, BuildConfig.GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS)
  }

  override fun onNotificationPosted(sbn: StatusBarNotification?) {
    val notification = sbn?.notification ?: return
    val extras = notification.extras ?: return
    var title: CharSequence? = extras.getCharSequence("android.title")
    var text: CharSequence? = extras.getCharSequence("android.text")
    try {
      ContentSafetyServiceRuntime.processNotification(
        context = this,
        trustedKeysJson = BuildConfig.GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS,
        packageName = sbn.packageName,
        isSystemNoise = isSystemNoise(sbn.packageName),
        notificationCategory = notification.category,
        channelId = notification.channelId,
        title = title,
        text = text,
      )
    } finally {
      // Notification text is transient local input only. Never log, bridge, or retain it.
      title = null
      text = null
    }
  }

  private fun isSystemNoise(packageName: String): Boolean {
    if (packageName == applicationContext.packageName) return true
    val info = runCatching { packageManager.getApplicationInfo(packageName, 0) }.getOrNull()
      ?: return true
    val isSystem = info.flags and (ApplicationInfo.FLAG_SYSTEM or ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0
    return isSystem && packageManager.getLaunchIntentForPackage(packageName) == null
  }
}
