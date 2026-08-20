package expo.modules.guardianprotection.content

import android.content.Context

/** Separate from a signed parent policy: this records an affirmative local accessibility disclosure choice. */
class ContentSafetyConsentStore(context: Context) {
  private val preferences = context.applicationContext.getSharedPreferences(
    "guardian-content-safety-consent",
    Context.MODE_PRIVATE,
  )

  fun hasAccessibilityContentConsent(): Boolean =
    preferences.getBoolean(ACCESSIBILITY_CONTENT_CONSENT, false)

  fun setAccessibilityContentConsent(granted: Boolean) {
    preferences.edit().putBoolean(ACCESSIBILITY_CONTENT_CONSENT, granted).commit()
  }

  private companion object {
    const val ACCESSIBILITY_CONTENT_CONSENT = "accessibility-content-consent"
  }
}
