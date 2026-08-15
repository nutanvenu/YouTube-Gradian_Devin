export type PairingAttempt =
  | { kind: "expired" }
  | { kind: "wrong-code"; attempts: number }
  | { kind: "revoked" }
  | { kind: "accepted" };

export function pairingMessage(attempt: PairingAttempt): string {
  if (attempt.kind === "expired") return "This pairing code has expired.";
  if (attempt.kind === "revoked") return "This device has been revoked.";
  if (attempt.kind === "wrong-code") {
    return attempt.attempts >= 5
      ? "Too many incorrect codes. Create a new pairing session."
      : "That code is incorrect.";
  }
  return "Device paired.";
}
