package expo.modules.guardianprotection.policy

import android.util.Base64
import java.security.KeyFactory
import java.security.PublicKey
import java.security.Signature
import java.security.spec.X509EncodedKeySpec

class PolicyVerifier(
  private val trustedKeys: Map<String, String> = emptyMap(),
) {
  fun verify(bundle: Map<String, Any?>): Boolean {
    val keyId = bundle["key_id"] as? String ?: return false
    val signature = bundle["signature"] as? String ?: return false
    val encodedKey = trustedKeys[keyId] ?: return false
    return runCatching {
      val publicKey = publicKey(Base64.decode(encodedKey, Base64.DEFAULT))
      val verifier = Signature.getInstance("Ed25519")
      verifier.initVerify(publicKey)
      verifier.update(CanonicalJson.unsignedBytes(bundle))
      verifier.verify(Base64.decode(signature, Base64.DEFAULT))
    }.getOrDefault(false)
  }

  private fun publicKey(bytes: ByteArray): PublicKey =
    KeyFactory.getInstance("Ed25519").generatePublic(X509EncodedKeySpec(bytes))
}
