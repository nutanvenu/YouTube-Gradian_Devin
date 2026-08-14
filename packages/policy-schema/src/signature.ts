import type { SignedPolicyBundle } from "./generated.js";
import { canonicalizeForSigning } from "./canonical.js";

function decodeBase64(value: string): Uint8Array {
  const binary = atob(value);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

export async function verifyPolicySignature(
  bundle: SignedPolicyBundle,
  publicKeyBase64: string
): Promise<boolean> {
  const key = await crypto.subtle.importKey(
    "raw",
    decodeBase64(publicKeyBase64),
    { name: "Ed25519" },
    false,
    ["verify"]
  );
  return crypto.subtle.verify(
    "Ed25519",
    key,
    decodeBase64(bundle.signature),
    canonicalizeForSigning(bundle)
  );
}
