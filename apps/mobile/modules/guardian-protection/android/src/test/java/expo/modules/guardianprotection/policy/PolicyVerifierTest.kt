package expo.modules.guardianprotection.policy

import java.security.KeyPairGenerator
import java.security.Signature
import java.util.Base64
import java.security.KeyFactory
import java.security.spec.X509EncodedKeySpec
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PolicyVerifierTest {
  @Test
  fun trustedKeyVerifiesAndTamperingOrRotationFails() {
    val pair = KeyPairGenerator.getInstance("Ed25519").generateKeyPair()
    val bundle = mutableMapOf<String, Any?>(
      "schema_version" to 1,
      "policy_version" to 1,
      "family_id" to "family",
      "child_profile_id" to "child",
      "issued_at" to "2026-01-01T00:00:00Z",
      "expires_soft_at" to "2026-01-08T00:00:00Z",
      "key_id" to "current",
      "base_policy" to emptyMap<String, Any?>(),
      "app_rules" to emptyList<Any?>(),
      "domain_rules" to emptyList<Any?>(),
      "category_rules" to emptyList<Any?>(),
      "routines" to emptyList<Any?>(),
      "temporary_overrides" to emptyList<Any?>(),
    )
    val signer = Signature.getInstance("Ed25519")
    signer.initSign(pair.private)
    signer.update(CanonicalJson.unsignedBytes(bundle))
    val encoder = Base64.getEncoder()
    val decoder = Base64.getDecoder()
    bundle["signature"] = encoder.encodeToString(signer.sign())
    val encodedKey = encoder.encodeToString(pair.public.encoded)
    val direct = Signature.getInstance("Ed25519")
    direct.initVerify(
        KeyFactory.getInstance("Ed25519")
        .generatePublic(X509EncodedKeySpec(decoder.decode(encodedKey))),
    )
    direct.update(CanonicalJson.unsignedBytes(bundle))
    assertTrue(direct.verify(decoder.decode(bundle["signature"] as String)))

    assertTrue(
      PolicyVerifier(mapOf("current" to encodedKey), decodeBase64 = decoder::decode).verify(bundle),
    )
    bundle["family_id"] = "tampered"
    assertFalse(
      PolicyVerifier(mapOf("current" to encodedKey), decodeBase64 = decoder::decode).verify(bundle),
    )
    bundle["family_id"] = "family"
    assertFalse(
      PolicyVerifier(mapOf("rotated-out" to encodedKey), decodeBase64 = decoder::decode).verify(bundle),
    )
  }
}
