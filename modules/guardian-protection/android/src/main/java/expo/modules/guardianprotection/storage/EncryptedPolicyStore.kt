package expo.modules.guardianprotection.storage

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.spec.GCMParameterSpec

class EncryptedPolicyStore(context: Context) {
  private val preferences = context.getSharedPreferences("guardian-protection", Context.MODE_PRIVATE)
  private val alias = "guardian-protection-state"

  fun active(): String? = read("active")
  fun previous(): String? = read("previous")
  fun appliedVersion(): Long? = preferences.getLong("applied-version", -1).takeIf { it >= 0 }

  fun swap(active: String, version: Long) {
    val old = read("active")
    preferences.edit()
      .putString("previous", old?.let { encrypt(it) })
      .putString("active", encrypt(active))
      .putLong("applied-version", version)
      .apply()
  }

  fun usageSummary(range: Map<String, Any?>): Map<String, Any?> = mapOf(
    "range" to range,
    "totalSeconds" to preferences.getLong("usage-total-seconds", 0),
    "byTarget" to emptyMap<String, Long>(),
  )

  private fun read(key: String): String? = preferences.getString(key, null)?.let(::decrypt)

  private fun key() = (KeyStore.getInstance("AndroidKeyStore").apply { load(null) }.getKey(alias, null)
    ?: KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
      init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
        .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
        .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
        .setUserAuthenticationRequired(false)
        .build())
    }.generateKey())

  private fun encrypt(value: String): String {
    val cipher = Cipher.getInstance("AES/GCM/NoPadding")
    cipher.init(Cipher.ENCRYPT_MODE, key())
    return Base64.encodeToString(cipher.iv + cipher.doFinal(value.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
  }

  private fun decrypt(value: String): String {
    val bytes = Base64.decode(value, Base64.NO_WRAP)
    val cipher = Cipher.getInstance("AES/GCM/NoPadding")
    cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(0, 12)))
    return cipher.doFinal(bytes.copyOfRange(12, bytes.size)).toString(Charsets.UTF_8)
  }
}
