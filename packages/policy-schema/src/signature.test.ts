import { webcrypto } from "node:crypto";
import { describe, expect, it } from "vitest";
import { canonicalizeForSigning } from "./canonical.js";
import type { SignedPolicyBundle } from "./generated.js";
import { verifyPolicySignature } from "./signature.js";

const bundle = {
  schema_version: 1,
  policy_version: 1,
  family_id: "family",
  child_profile_id: "child",
  issued_at: "2026-01-01T00:00:00Z",
  expires_soft_at: "2026-01-08T00:00:00Z",
  age_band: "TEEN",
  base_policy: {
    timezone: "UTC",
    unknown_domain_policy: "ALLOW_AND_NOTIFY",
    unknown_app_policy: "ALLOW_AND_NOTIFY",
    hard_category_rules: [],
    default_category_rules: [],
    safety_allowlist: []
  },
  app_rules: [],
  domain_rules: [],
  category_rules: [],
  routines: [],
  temporary_overrides: [],
  communication_safety: {
    enabled: false,
    severity_threshold: "HIGH",
    android_notification_signals: false,
    android_accessibility_signals: false
  },
  signature: ""
} satisfies SignedPolicyBundle;

describe("Ed25519 policy signatures", () => {
  it("verifies a signature over canonical bundle bytes and rejects tampering", async () => {
    const keyPair = (await webcrypto.subtle.generateKey(
      { name: "Ed25519" },
      true,
      ["sign", "verify"]
    )) as CryptoKeyPair;
    const signature = await webcrypto.subtle.sign(
      "Ed25519",
      keyPair.privateKey,
      canonicalizeForSigning(bundle)
    );
    const publicKey = await webcrypto.subtle.exportKey("raw", keyPair.publicKey);
    const signedBundle = {
      ...bundle,
      signature: Buffer.from(signature).toString("base64")
    };

    await expect(
      verifyPolicySignature(signedBundle, Buffer.from(publicKey).toString("base64"))
    ).resolves.toBe(true);
    await expect(
      verifyPolicySignature(
        { ...signedBundle, policy_version: 2 },
        Buffer.from(publicKey).toString("base64")
      )
    ).resolves.toBe(false);
  });
});
