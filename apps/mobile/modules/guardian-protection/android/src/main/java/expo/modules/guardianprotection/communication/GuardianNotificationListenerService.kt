package expo.modules.guardianprotection.communication

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

class GuardianNotificationListenerService : NotificationListenerService() {
  override fun onNotificationPosted(sbn: StatusBarNotification?) {
    val notification = sbn?.notification ?: return
    val extras = notification.extras ?: return
    val title = extras.getCharSequence("android.title")?.toString()
    val text = extras.getCharSequence("android.text")?.toString()
    CommunicationSafetyRuntime.processNotification(sbn.packageName, title, text)
  }
}
