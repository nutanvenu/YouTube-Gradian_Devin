package expo.modules.guardianprotection.storage

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.util.concurrent.atomic.AtomicBoolean
import org.json.JSONObject
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.spec.GCMParameterSpec
import expo.modules.guardianprotection.usage.deviceTotalSeconds

class EncryptedPolicyStore(
  context: Context,
  preferenceName: String = "guardian-protection",
) {
  private val preferences = context.getSharedPreferences(preferenceName, Context.MODE_PRIVATE)
  private val alias = "guardian-protection-state"
  private val corruptState = AtomicBoolean(false)

  fun active(): String? = read("active")
  fun previous(): String? = read("previous")
  fun appliedVersion(): Long? = preferences.getLong("applied-version", -1).takeIf { it >= 0 }
  fun hasCorruptState(): Boolean = corruptState.get()

  fun swap(active: String, version: Long) {
    val old = read("active")
    preferences.edit()
      .putString("previous", old?.let { encrypt(it) })
      .putString("active", encrypt(active))
      .putLong("applied-version", version)
      .commit()
  }

  @Synchronized
  fun addUsage(target: String, deltaSeconds: Long, elapsedRealtime: Long) {
    require(target.isNotBlank()) { "Usage target cannot be blank" }
    require(deltaSeconds >= 0) { "Usage deltas cannot be negative" }
    require(elapsedRealtime >= 0) { "Elapsed realtime cannot be negative" }
    val counters = usageCounters()
    val current = counters[target] ?: CounterState()
    val next = MonotonicCounterStore().also {
      it.restore(current.totalSeconds, current.lastElapsedRealtime)
    }.add(deltaSeconds, elapsedRealtime)
    counters[target] = CounterState(next, elapsedRealtime)
    val json = JSONObject().apply {
      counters.toSortedMap().forEach { (key, value) ->
        put(key, JSONObject().apply {
          put("total_seconds", value.totalSeconds)
          put("last_elapsed_realtime", value.lastElapsedRealtime)
        })
      }
    }
    preferences.edit().putString("usage-counters", encrypt(json.toString())).commit()
  }

  fun usageSummary(range: Map<String, Any?>): Map<String, Any?> {
    val byTarget = usageCounters().mapValues { it.value.totalSeconds }
    return mapOf(
      "range" to range,
      "totalSeconds" to deviceTotalSeconds(byTarget),
      "byTarget" to byTarget,
    )
  }

  @Synchronized
  fun mergeUsageSnapshot(date: String, totals: Map<String, Long>) {
    require(date.isNotBlank()) { "Usage date cannot be blank" }
    require(totals.values.all { it >= 0 }) { "Usage totals cannot be negative" }
    val root = usageSnapshots().toMutableMap()
    val current = root[date].orEmpty().toMutableMap()
    totals.forEach { (target, value) ->
      if (target.isNotBlank()) current[target] = maxOf(current[target] ?: 0L, value)
    }
    root[date] = current
    val json = JSONObject().apply {
      root.toSortedMap().forEach { (day, values) ->
        put(day, JSONObject().apply {
          values.toSortedMap().forEach { (target, total) -> put(target, total) }
        })
      }
    }
    preferences.edit().putString("usage-snapshots", encrypt(json.toString())).commit()
  }

  fun usageSnapshots(): Map<String, Map<String, Long>> {
    val encoded = preferences.getString("usage-snapshots", null) ?: return emptyMap()
    val decoded = runCatching { JSONObject(decrypt(encoded)) }.getOrElse {
      corruptState.set(true)
      return emptyMap()
    }
    return decoded.keys().asSequence().associateWith { day ->
      val values = decoded.getJSONObject(day)
      values.keys().asSequence().associateWith { target -> values.getLong(target) }
    }
  }

  private fun read(key: String): String? {
    val encoded = preferences.getString(key, null) ?: return null
    return runCatching { decrypt(encoded) }.getOrElse {
      corruptState.set(true)
      null
    }
  }

  private fun usageCounters(): MutableMap<String, CounterState> {
    val encoded = preferences.getString("usage-counters", null) ?: return mutableMapOf()
    val decoded = runCatching { JSONObject(decrypt(encoded)) }.getOrElse {
      corruptState.set(true)
      throw IllegalStateException("Encrypted usage state is corrupt", it)
    }
    return decoded.keys().asSequence().associateWith { key ->
      val value = decoded.getJSONObject(key)
      CounterState(
        value.getLong("total_seconds"),
        value.getLong("last_elapsed_realtime"),
      )
    }.toMutableMap()
  }

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

  private data class CounterState(
    val totalSeconds: Long = 0,
    val lastElapsedRealtime: Long = 0,
  )
}
