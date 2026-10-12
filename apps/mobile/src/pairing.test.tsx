import type { ReactNode } from "react";
import { act, render, waitFor } from "@testing-library/react-native";
import type { Pairing } from "@/api/client";
import ParentPairingRoute from "./app/parent/pairing";

let mockParams = { familyId: "family-1", childId: "child-1" };
const mockCreatePairing = jest.fn<Promise<Pairing>, [string, string]>();

jest.mock("expo-router", () => ({ useLocalSearchParams: () => mockParams }));
jest.mock("@/api/client", () => ({
  api: { createPairing: (familyId: string, childId: string) => mockCreatePairing(familyId, childId) },
}));
jest.mock("react-native-qrcode-svg", () => () => null);
jest.mock("@/design-system", () => {
  const { Text, View, Pressable } = jest.requireActual<typeof import("react-native")>("react-native");
  const Surface = ({ children }: { children: ReactNode }) => <View>{children}</View>;
  return {
    ScreenScaffold: Surface,
    SectionSurface: Surface,
    DataState: ({ state, children }: { state: string; children: ReactNode }) => state === "loaded" ? <View>{children}</View> : <Text>{state}</Text>,
    PrimaryButton: ({ label, onPress }: { label: string; onPress: () => void }) => <Pressable onPress={onPress}><Text>{label}</Text></Pressable>,
  };
});

function pendingPairing() {
  let resolve!: (value: Pairing) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<Pairing>((accept, fail) => { resolve = accept; reject = fail; });
  return { promise, resolve, reject };
}

it.each(["success", "failure"] as const)("ignores stale pairing %s after the selected child changes", async (outcome) => {
  mockCreatePairing.mockReset();
  mockParams = { familyId: "family-1", childId: "child-1" };
  const old = pendingPairing();
  const fresh = pendingPairing();
  mockCreatePairing.mockReturnValueOnce(old.promise).mockReturnValueOnce(fresh.promise);
  const screen = render(<ParentPairingRoute />);
  await waitFor(() => expect(mockCreatePairing).toHaveBeenCalledTimes(1));
  mockParams = { familyId: "family-2", childId: "child-2" };
  screen.rerender(<ParentPairingRoute />);
  await waitFor(() => expect(mockCreatePairing).toHaveBeenCalledTimes(2));
  const value = { session_id: "fresh", code: "NEW123", qr_payload: "guardian://fresh", expires_at: new Date(Date.now() + 60_000).toISOString() };
  await act(async () => { fresh.resolve(value); await fresh.promise; });
  expect(screen.getByText("Manual code: NEW123")).toBeTruthy();
  await act(async () => {
    if (outcome === "success") old.resolve({ ...value, code: "OLD123" });
    else old.reject(new Error("Late response"));
    await old.promise.catch(() => undefined);
  });
  expect(screen.getByText("Manual code: NEW123")).toBeTruthy();
  expect(screen.queryByText("error")).toBeNull();
  expect(screen.queryByText("Manual code: OLD123")).toBeNull();
});
