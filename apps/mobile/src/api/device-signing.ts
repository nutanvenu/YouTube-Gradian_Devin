import * as Crypto from "expo-crypto";
import * as ed25519 from "@noble/ed25519";

ed25519.hashes.sha512Async = async (message) =>
  new Uint8Array(
    await Crypto.digest(Crypto.CryptoDigestAlgorithm.SHA512, new Uint8Array(message)),
  );

function fromBase64(value: string): Uint8Array {
  const binary = globalThis.atob(value);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

export function toBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return globalThis.btoa(binary);
}

export async function signDeviceRequest(
  privateKey: string,
  method: string,
  path: string,
  timestamp: string,
  nonce: string,
  body: string,
): Promise<string> {
  const digest = new Uint8Array(
    await Crypto.digest(
      Crypto.CryptoDigestAlgorithm.SHA256,
      new TextEncoder().encode(body),
    ),
  );
  const bodyHash = Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("");
  const message = `${method.toUpperCase()}\n${path}\n${timestamp}\n${nonce}\n${bodyHash}`;
  return toBase64(await ed25519.signAsync(new TextEncoder().encode(message), fromBase64(privateKey)));
}
