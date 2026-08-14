import type { SignedPolicyBundle } from "./generated.js";

type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

function escapeString(value: string): string {
  return JSON.stringify(value);
}

function canonicalize(value: JsonValue): string {
  if (value === null || typeof value === "boolean" || typeof value === "number") {
    return JSON.stringify(value);
  }
  if (typeof value === "string") {
    return escapeString(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(canonicalize).join(",")}]`;
  }
  const keys = Object.keys(value).sort((left, right) => left < right ? -1 : left > right ? 1 : 0);
  return `{${keys.map((key) => `${escapeString(key)}:${canonicalize(value[key] as JsonValue)}`).join(",")}}`;
}

export function canonicalizeForSigning(bundle: SignedPolicyBundle): Uint8Array {
  const unsigned = Object.fromEntries(
    Object.entries(bundle).filter(([key]) => key !== "signature")
  );
  return new TextEncoder().encode(canonicalize(unsigned as unknown as JsonValue));
}
