package expo.modules.guardianprotection.policy

import android.util.Base64
import org.bouncycastle.jce.provider.BouncyCastleProvider
import java.security.KeyFactory
import java.security.PublicKey
import java.security.Security
import java.security.Signature
import java.security.spec.X509EncodedKeySpec

class PolicyVerifier(
  private val trustedKeys: Map<String, String> = emptyMap(),
  private val decodeBase64: (String) -> ByteArray = { Base64.decode(it, Base64.DEFAULT) },
) {
  init {
    val provider = Security.getProvider("BC")
    if (provider?.getService("KeyFactory", "Ed25519") == null) {
      Security.removeProvider("BC")
      Security.addProvider(BouncyCastleProvider())
    }
  }

  fun verify(bundle: Map<String, Any?>): Boolean {
    val keyId = bundle["key_id"] as? String ?: return false
    val signature = bundle["signature"] as? String ?: return false
    val encodedKey = trustedKeys[keyId] ?: return false
    return runCatching {
      val publicKey = publicKey(decodeBase64(encodedKey))
      val verifier = Signature.getInstance("Ed25519", "BC")
      verifier.initVerify(publicKey)
      verifier.update(CanonicalJson.unsignedBytes(bundle))
      verifier.verify(decodeBase64(signature))
    }.getOrDefault(false)
  }

  private fun publicKey(bytes: ByteArray): PublicKey {
    val encoded = if (bytes.size == 32) {
      byteArrayOf(
        0x30, 0x2a, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x03, 0x21, 0x00,
      ) + bytes
    } else {
      bytes
    }
    return KeyFactory.getInstance("Ed25519", "BC")
      .generatePublic(X509EncodedKeySpec(encoded))
  }
}
