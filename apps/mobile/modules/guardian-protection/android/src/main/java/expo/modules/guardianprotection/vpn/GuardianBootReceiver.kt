package expo.modules.guardianprotection.vpn

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class GuardianBootReceiver : BroadcastReceiver() {
  override fun onReceive(context: Context, intent: Intent) {
    if (intent.action == Intent.ACTION_BOOT_COMPLETED && GuardianVpnPreferences.isEnabled(context)) {
      GuardianVpnService.startWithPersistedPolicy(context)
    }
  }
}
