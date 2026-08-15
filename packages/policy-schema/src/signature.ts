import type { SignedPolicyBundle } from "./generated.js";
import { canonicalizeForSigning } from "./canonical.js";
import type { PolicyDecision } from "@guardian/contracts";

function decodeBase64(value: string): Uint8Array {
  const binary = atob(value);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

declare const verifiedPolicyBundleBrand: unique symbol;
export type VerifiedPolicyBundle = SignedPolicyBundle & {
  readonly [verifiedPolicyBundleBrand]: true;
};

export class BundleVerificationError extends Error {
  constructor(message = "Policy bundle signature verification failed") {
    super(message);
    this.name = "BundleVerificationError";
  }
}

export async function verifyPolicySignature(
  bundle: SignedPolicyBundle,
  publicKeyBase64: string
): Promise<boolean> {
  try {
    const key = await crypto.subtle.importKey(
      "raw",
      decodeBase64(publicKeyBase64),
      { name: "Ed25519" },
      false,
      ["verify"]
    );
    return await crypto.subtle.verify(
      "Ed25519",
      key,
      decodeBase64(bundle.signature),
      canonicalizeForSigning(bundle)
    );
  } catch {
    return false;
  }
}

export async function verifyBundle(
  bundle: SignedPolicyBundle,
  publicKeyBase64: string
): Promise<VerifiedPolicyBundle> {
  if (!(await verifyPolicySignature(bundle, publicKeyBase64))) {
    throw new BundleVerificationError();
  }
  return bundle as VerifiedPolicyBundle;
}

export async function verifyBundleAgainstTrustedKeys(
  bundle: SignedPolicyBundle,
  trustedPublicKeys: Readonly<Record<string, string>>
): Promise<VerifiedPolicyBundle> {
  const keyId = bundle.key_id;
  const publicKey = trustedPublicKeys[keyId];
  if (!publicKey || !(await verifyPolicySignature(bundle, publicKey))) {
    throw new BundleVerificationError("Policy bundle key is not trusted");
  }
  return bundle as VerifiedPolicyBundle;
}

export function unsafeTrustBundleForTesting(
  bundle: SignedPolicyBundle
): VerifiedPolicyBundle {
  return bundle as VerifiedPolicyBundle;
}

export function tamperedSignatureDecision(): PolicyDecision {
  return {
    action: "BLOCK",
    reason_code: "TAMPERED_SIGNATURE",
    policy_rule_id: null,
    bundle_stale: false
  };
}
