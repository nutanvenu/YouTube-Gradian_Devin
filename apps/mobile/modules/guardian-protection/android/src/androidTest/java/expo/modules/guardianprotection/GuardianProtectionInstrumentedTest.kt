package expo.modules.guardianprotection

import android.content.Context
import android.app.AppOpsManager
import android.os.Process
import android.util.Base64
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import expo.modules.guardianprotection.health.CapabilityDetector
import expo.modules.guardianprotection.inventory.PackageInventory
import expo.modules.guardianprotection.policy.CanonicalJson
import expo.modules.guardianprotection.policy.GuardianPolicyRuntime
import expo.modules.guardianprotection.policy.PolicyManager
import expo.modules.guardianprotection.storage.EncryptedPolicyStore
import expo.modules.guardianprotection.usage.UsageContext
import java.security.KeyPairGenerator
import java.security.KeyPair
import java.security.Security
import java.security.Signature
import java.security.MessageDigest
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import org.json.JSONArray
import org.json.JSONObject
import org.bouncycastle.jce.provider.BouncyCastleProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class GuardianProtectionInstrumentedTest {
  @Test
  fun reportsRealCapabilitiesAndAppliesSignedPolicy() {
    val context = ApplicationProvider.getApplicationContext<Context>()
    val capabilities = CapabilityDetector(context).getCapabilities()
    assertTrue(capabilities.isNotEmpty())
    assertTrue(capabilities.values.all { it["level"] is String })

    val provider = Security.getProvider("BC")
    if (provider?.getService("KeyFactory", "Ed25519") == null) {
      Security.removeProvider("BC")
      Security.addProvider(BouncyCastleProvider())
    }
    val email = "native-${System.currentTimeMillis()}@example.com"
    val password = "Guardian!Native1234"
    val tokens = request(
      "/v1/auth/signup",
      "POST",
      body = JSONObject().apply {
        put("email", email)
        put("password", password)
      },
    )
    val accessToken = tokens.getString("access_token")
    val family = request(
      "/v1/families",
      "POST",
      accessToken,
      JSONObject().put("name", "Native Test Family"),
    )
    val familyId = family.getString("id")
    val child = request(
      "/v1/families/$familyId/children",
      "POST",
      accessToken,
      JSONObject().apply {
        put("name", "Native Test Child")
        put("date_of_birth", "2012-01-01")
        put("timezone", "UTC")
      },
    )
    val childId = child.getString("id")
    request(
      "/v1/families/$familyId/children/$childId/policy/mutations",
      "POST",
      accessToken,
      JSONObject().apply {
        put("operation", "APP_BLOCK")
        put("target", "com.example.blocked")
      },
    )
    val pairing = request(
      "/v1/families/$familyId/children/$childId/pairing",
      "POST",
      accessToken,
    )
    val keyPair = KeyPairGenerator.getInstance("Ed25519", "BC").generateKeyPair()
    val credentials = request(
      "/v1/devices/pair",
      "POST",
      body = JSONObject().apply {
        put("session_id", pairing.getString("session_id"))
        put("code", pairing.getString("code"))
        put("child_profile_id", childId)
        put("platform", "ANDROID")
        put(
          "public_key",
          Base64.encodeToString(keyPair.public.encoded.takeLast(32).toByteArray(), Base64.NO_WRAP),
        )
      },
    )
    val policyResponse = request(
      "/v1/devices/me/policy",
      "GET",
      credentials.getString("device_token"),
    )
    val publicKeyResponse = request("/v1/policy/public-key", "GET")
    val bundle = jsonObjectToMap(policyResponse.getJSONObject("bundle"))
    val trustedKeys = publicKeyResponse.getJSONObject("trusted_public_keys").toString()
    val manager = PolicyManager(
      EncryptedPolicyStore(context, "guardian-native-test-${System.currentTimeMillis()}"),
      trustedKeys,
    )
    val result = manager.apply(bundle)

    assertEquals(result.toString(), true, result["applied"])
    assertEquals(policyResponse.getLong("policy_version"), result["policyVersion"])
    GuardianPolicyRuntime.install(manager)
    val decision = GuardianPolicyRuntime.evaluateApp(
      "com.example.blocked",
      null,
      UsageContext(appMillis = 0, categoryMillis = 0, deviceMillis = 0),
    )
    assertTrue("Signed APP_BLOCK policy must block the app", decision.blocked)

    val requestBody = JSONObject().apply {
      put("request_type", "UNBLOCK_APP")
      put("subject", "com.example.blocked")
      put("reason", "Need this app for homework")
    }
    val accessRequest = signedRequest(
      "/v1/devices/me/requests",
      "POST",
      credentials.getString("device_token"),
      keyPair,
      requestBody,
    )
    assertEquals("PENDING", accessRequest.getString("state"))
    val requests = requestArray("/v1/families/$familyId/requests", "GET", accessToken)
    assertTrue((0 until requests.length()).any { requests.getJSONObject(it).getString("id") == accessRequest.getString("id") })
    val approved = request(
      "/v1/families/$familyId/requests/${accessRequest.getString("id")}/approve",
      "POST",
      accessToken,
      JSONObject().put("reason", "Approved for homework"),
    )
    assertEquals("APPROVED", approved.getString("state"))
  }

  @Test
  fun inventoryUsesRealPackageManagerDataAndCapabilityLevelsAreTruthful() {
    val context = ApplicationProvider.getApplicationContext<Context>()
    val inventory = PackageInventory(context).observedApps()
    assertTrue("Package manager inventory should contain visible apps", inventory.isNotEmpty())
    assertTrue(inventory.all { it["platformAppId"] is String && it["displayName"] is String })
    val capabilities = CapabilityDetector(context).getCapabilities()
    val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
    val granted = appOps.checkOpNoThrow(
      AppOpsManager.OPSTR_GET_USAGE_STATS,
      Process.myUid(),
      context.packageName,
    ) == AppOpsManager.MODE_ALLOWED
    assertEquals(if (granted) "FULL" else "UNAVAILABLE", capabilities.getValue("app_usage").getValue("level"))
  }

  private fun request(
    path: String,
    method: String,
    bearer: String? = null,
    body: JSONObject? = null,
  ): JSONObject {
    val connection = (URL("http://10.0.2.2:8000$path").openConnection() as HttpURLConnection).apply {
      requestMethod = method
      connectTimeout = 15_000
      readTimeout = 15_000
      setRequestProperty("Content-Type", "application/json")
      bearer?.let { setRequestProperty("Authorization", "Bearer $it") }
      if (body != null) {
        doOutput = true
        outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
      }
    }
    val responseBody = (if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream)
      .bufferedReader()
      .use { it.readText() }
    assertTrue("Backend request $method $path failed (${connection.responseCode}): $responseBody", connection.responseCode in 200..299)
    return JSONObject(responseBody)
  }

  private fun signedRequest(
    path: String,
    method: String,
    bearer: String,
    keyPair: KeyPair,
    body: JSONObject,
  ): JSONObject {
    val bodyBytes = body.toString().toByteArray(Charsets.UTF_8)
    val timestamp = (System.currentTimeMillis() / 1000).toString()
    val nonce = UUID.randomUUID().toString()
    val digest = MessageDigest.getInstance("SHA-256").digest(bodyBytes)
      .joinToString("") { "%02x".format(it) }
    val message = "$method\n$path\n$timestamp\n$nonce\n$digest".toByteArray(Charsets.UTF_8)
    val signer = Signature.getInstance("Ed25519", "BC").apply {
      initSign(keyPair.private)
      update(message)
    }
    val connection = (URL("http://10.0.2.2:8000$path").openConnection() as HttpURLConnection).apply {
      requestMethod = method
      connectTimeout = 15_000
      readTimeout = 15_000
      doOutput = true
      setRequestProperty("Content-Type", "application/json")
      setRequestProperty("Authorization", "Bearer $bearer")
      setRequestProperty("X-Guardian-Device-Timestamp", timestamp)
      setRequestProperty("X-Guardian-Device-Nonce", nonce)
      setRequestProperty(
        "X-Guardian-Device-Signature",
        Base64.encodeToString(signer.sign(), Base64.NO_WRAP),
      )
      outputStream.use { it.write(bodyBytes) }
    }
    val responseBody = (if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream)
      .bufferedReader()
      .use { it.readText() }
    assertTrue("Signed backend request $method $path failed (${connection.responseCode}): $responseBody", connection.responseCode in 200..299)
    return JSONObject(responseBody)
  }

  private fun requestArray(
    path: String,
    method: String,
    bearer: String? = null,
  ): JSONArray {
    val connection = (URL("http://10.0.2.2:8000$path").openConnection() as HttpURLConnection).apply {
      requestMethod = method
      connectTimeout = 15_000
      readTimeout = 15_000
      setRequestProperty("Content-Type", "application/json")
      bearer?.let { setRequestProperty("Authorization", "Bearer $it") }
    }
    val responseBody = (if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream)
      .bufferedReader()
      .use { it.readText() }
    assertTrue("Backend request $method $path failed (${connection.responseCode}): $responseBody", connection.responseCode in 200..299)
    return JSONArray(responseBody)
  }

  private fun jsonObjectToMap(value: JSONObject): MutableMap<String, Any?> =
    value.keys().asSequence().associateWith { key -> jsonValue(value.get(key)) }.toMutableMap()

  private fun jsonValue(value: Any?): Any? = when (value) {
    JSONObject.NULL -> null
    is JSONObject -> jsonObjectToMap(value)
    is JSONArray -> (0 until value.length()).map { jsonValue(value.get(it)) }
    else -> value
  }
}
