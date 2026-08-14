package expo.modules.guardianprotection.inventory

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.net.Uri
import java.time.Instant

class PackageInventory(private val context: Context) {
  private val preferences = context.getSharedPreferences("guardian-inventory", Context.MODE_PRIVATE)

  fun observedApps(): List<Map<String, Any?>> {
    val packageManager = context.packageManager
    val apps = packageManager.getInstalledApplications(PackageManager.GET_META_DATA)
      .filter { it.packageName != context.packageName }
      .sortedBy { packageManager.getApplicationLabel(it).toString().lowercase() }
    val newDetector = NewAppDetector(
      preferences.getStringSet("known-packages", emptySet()).orEmpty().toMutableSet(),
    )
    val newlyObserved = newDetector.newPackages(apps.map { it.packageName })
    preferences.edit().putStringSet("known-packages", apps.map { it.packageName }.toSet()).apply()
    val observedAt = Instant.now().toString()
    return apps.map { application ->
      val icon = application.icon.takeIf { it != 0 }?.let {
        Uri.Builder()
          .scheme("android.resource")
          .authority(application.packageName)
          .appendPath(it.toString())
          .build()
          .toString()
      }
      mapOf(
        "platformAppId" to application.packageName,
        "displayName" to packageManager.getApplicationLabel(application).toString(),
        "category" to category(application),
        "iconUri" to icon,
        "newlyObserved" to newlyObserved.contains(application.packageName),
        "observedAt" to observedAt,
      )
    }
  }

  fun category(packageName: String): String =
    runCatching { category(packageManager().getApplicationInfo(packageName, 0)) }.getOrDefault("UNKNOWN")

  fun categoryFor(packageName: String): String = category(packageName)

  private fun packageManager(): PackageManager = context.packageManager

  private fun category(application: ApplicationInfo): String =
    when {
      application.category == ApplicationInfo.CATEGORY_GAME -> "GAMES"
      application.category == ApplicationInfo.CATEGORY_AUDIO -> "MUSIC"
      application.category == ApplicationInfo.CATEGORY_VIDEO -> "STREAMING_VIDEO"
      application.category == ApplicationInfo.CATEGORY_IMAGE -> "CREATIVE"
      (application.flags and ApplicationInfo.FLAG_SYSTEM) != 0 -> "SYSTEM"
      else -> "UNKNOWN"
    }
}
