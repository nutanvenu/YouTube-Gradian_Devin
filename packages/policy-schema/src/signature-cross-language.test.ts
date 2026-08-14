import { describe, expect, it } from "vitest";
import { canonicalizeForSigning } from "./canonical.js";
import {
  verifyBundleAgainstTrustedKeys,
  verifyPolicySignature,
} from "./signature.js";
import type { SignedPolicyBundle } from "./generated.js";
import fixture from "../test-fixtures/signature-cross-language.json" with { type: "json" };

function bytesFromHex(value: string): Uint8Array {
  return Uint8Array.from(value.match(/.{2}/g) ?? [], (byte) => parseInt(byte, 16));
}

function privateKeyPkcs8(seed: string): Uint8Array {
  const prefix = bytesFromHex("302e020100300506032b657004220420");
  const key = bytesFromHex(seed);
  return Uint8Array.from([...prefix, ...key]);
}

function encodeBase64(value: ArrayBuffer): string {
  return Buffer.from(value).toString("base64");
}

describe("cross-language signature fixture", () => {
  it("signs the shared fixture with TypeScript and verifies the Python vector", async () => {
    const bundle = fixture.bundle as unknown as SignedPolicyBundle;
    const key = await crypto.subtle.importKey(
      "pkcs8",
      privateKeyPkcs8(fixture.private_key_seed),
      { name: "Ed25519" },
      false,
      ["sign"]
    );
    const signature = encodeBase64(
      await crypto.subtle.sign("Ed25519", key, canonicalizeForSigning(bundle))
    );
    expect(signature).toBe(fixture.signature);
    await expect(
      verifyPolicySignature(
        { ...bundle, signature: fixture.signature },
        fixture.public_key
      )
    ).resolves.toBe(true);
    await expect(
      verifyBundleAgainstTrustedKeys(
        { ...bundle, signature: fixture.signature },
        { "fixture-key": fixture.public_key }
      )
    ).resolves.toBeDefined();
    await expect(
      verifyBundleAgainstTrustedKeys(
        { ...bundle, signature: fixture.signature },
        { "rotated-out": fixture.public_key }
      )
    ).rejects.toThrow();
  });
});
