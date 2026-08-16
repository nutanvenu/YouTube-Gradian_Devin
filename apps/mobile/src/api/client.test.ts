import { ApiError, GuardianApiClient } from "@/api/client";
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

test("shares one refresh across concurrent parent requests", async () => {
  const values: Record<string, string | null> = {
    "guardian.access-token": "expired-access",
    "guardian.refresh-token": "refresh-token",
    "guardian.device-token": "paired-child-device",
  };
  (SecureStore.getItemAsync as jest.Mock).mockImplementation((key: string) => Promise.resolve(values[key] ?? null));
  (SecureStore.setItemAsync as jest.Mock).mockImplementation((key: string, value: string) => {
    values[key] = value;
    return Promise.resolve();
  });
  const requestUrlFor = (url: RequestInfo | URL) => (
    typeof url === "string" ? url : url instanceof URL ? url.href : url.url
  );
  const fetcher = jest.spyOn(globalThis, "fetch").mockImplementation((url, init) => {
    const requestUrl = requestUrlFor(url);
    if (requestUrl.endsWith("/v1/auth/refresh")) {
      return Promise.resolve(new Response(JSON.stringify({ access_token: "new-access", refresh_token: "new-refresh" }), { status: 200 }));
    }
    const authorization = new Headers(init?.headers).get("Authorization");
    return Promise.resolve(authorization === "Bearer new-access"
      ? new Response(JSON.stringify({ id: "p1", email: "parent@example.com" }), { status: 200 })
      : new Response(JSON.stringify({ error: { message: "expired" } }), { status: 401 }));
  });

  const client = new GuardianApiClient("https://guardian.test");
  await expect(Promise.all([client.me(), client.me()])).resolves.toHaveLength(2);
  expect(fetcher.mock.calls.filter(([url]) => requestUrlFor(url).endsWith("/v1/auth/refresh"))).toHaveLength(1);
  expect(values["guardian.device-token"]).toBe("paired-child-device");
  fetcher.mockRestore();
});

test("clears only parent auth and exposes an actionable error when refresh expires", async () => {
  const values: Record<string, string | null> = {
    "guardian.access-token": "expired-access",
    "guardian.refresh-token": "refresh-token",
    "guardian.device-token": "paired-child-device",
    "guardian.device-private-key": "private-key",
    "guardian.family-id": "family-1",
  };
  (SecureStore.getItemAsync as jest.Mock).mockImplementation((key: string) => Promise.resolve(values[key] ?? null));
  (SecureStore.deleteItemAsync as jest.Mock).mockImplementation((key: string) => {
    values[key] = null;
    return Promise.resolve();
  });
  const fetcher = jest.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: "expired" } }), { status: 401 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: "expired refresh" } }), { status: 401 }));

  await expect(new GuardianApiClient("https://guardian.test").me()).rejects.toMatchObject<Partial<ApiError>>({
    status: 401,
    code: "SESSION_EXPIRED",
    message: "Your parent session has expired. Sign in again.",
  });
  expect(values).toMatchObject({
    "guardian.access-token": null,
    "guardian.refresh-token": null,
    "guardian.device-token": "paired-child-device",
    "guardian.device-private-key": "private-key",
    "guardian.family-id": "family-1",
  });
  fetcher.mockRestore();
});

test("uses a stable request-specific key for parent approval retries", async () => {
  (SecureStore.getItemAsync as jest.Mock).mockImplementation((key: string) => (
    Promise.resolve(key === "guardian.access-token" ? "parent-access" : null)
  ));
  const fetcher = jest.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ id: "request-1", state: "APPROVED" }), { status: 200 }),
  );

  await new GuardianApiClient("https://guardian.test").decideRequest(
    "family-1", "request-1", "approve", "Approved",
  );
  const [, init] = fetcher.mock.calls[0];
  expect(new Headers(init?.headers).get("Idempotency-Key")).toBe(
    "request-decision:request-1:approve",
  );
  fetcher.mockRestore();
});
