import type { SignedPolicyBundle } from "./generated.js";

function escapeString(value: string): string {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    const next = value.charCodeAt(index + 1);
    if (code >= 0xd800 && code <= 0xdbff) {
      if (!(next >= 0xdc00 && next <= 0xdfff)) {
        throw new TypeError("Canonical JSON does not permit lone surrogates");
      }
      index += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      throw new TypeError("Canonical JSON does not permit lone surrogates");
    }
  }
  const serialized = JSON.stringify(value);
  return serialized;
}

function canonicalize(value: unknown): string {
  if (value === undefined) {
    throw new TypeError("Canonical JSON cannot serialize undefined");
  }
  if (value === null || typeof value === "boolean") return JSON.stringify(value);
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value)) {
      throw new TypeError("Canonical JSON permits only finite safe integers");
    }
    return JSON.stringify(value);
  }
  if (typeof value === "string") {
    return escapeString(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(canonicalize).join(",")}]`;
  }
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const keys = Object.keys(record).sort((left, right) =>
      left < right ? -1 : left > right ? 1 : 0
    );
    return `{${keys.map((key) => `${escapeString(key)}:${canonicalize(record[key])}`).join(",")}}`;
  }
  throw new TypeError("Canonical JSON encountered an unsupported value");
}

export function canonicalizeForSigning(bundle: SignedPolicyBundle): Uint8Array {
  const unsigned = Object.fromEntries(
    Object.entries(bundle).filter(([key]) => key !== "signature")
  );
  return new TextEncoder().encode(canonicalize(unsigned));
}
