import { GuardianApiClient } from "@/api/client";
import * as SecureStore from "expo-secure-store";

jest.mock("@/api/device-signing", () => ({
  signDeviceRequest: jest.fn(),
}));
jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

test("API client sends parent credentials and parses structured responses", async () => {
  const fetcher = jest.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "p1", email: "parent@example.com" }), { status: 200 }));
  const client = new GuardianApiClient("https://guardian.test");
  await expect(client.me()).resolves.toEqual({ id: "p1", email: "parent@example.com" });
  expect(fetcher).toHaveBeenCalledWith("https://guardian.test/v1/auth/me", expect.objectContaining({ headers: expect.any(Headers) }));
  fetcher.mockRestore();
});

test("refreshes once and retries a parent request after a 401", async () => {
  (SecureStore.getItemAsync as jest.Mock)
    .mockResolvedValueOnce("expired-access")
    .mockResolvedValueOnce(null)
    .mockResolvedValueOnce("refresh-token");
  const fetcher = jest
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: "expired" } }), { status: 401 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "new-access", refresh_token: "new-refresh" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ id: "p1", email: "parent@example.com" }), { status: 200 }));
  await expect(new GuardianApiClient("https://guardian.test").me()).resolves.toMatchObject({ id: "p1" });
  expect(fetcher).toHaveBeenCalledTimes(3);
  fetcher.mockRestore();
});
