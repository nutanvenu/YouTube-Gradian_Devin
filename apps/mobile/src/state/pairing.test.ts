import { pairingMessage } from "@/state/pairing";

test.each([
  [{ kind: "expired" }, "This pairing code has expired."],
  [{ kind: "wrong-code", attempts: 1 }, "That code is incorrect."],
  [{ kind: "wrong-code", attempts: 5 }, "Too many incorrect codes. Create a new pairing session."],
  [{ kind: "revoked" }, "This device has been revoked."],
] as const)("renders honest pairing state: %j", (state, message) => {
  expect(pairingMessage(state)).toBe(message);
});
