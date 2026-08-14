import * as SecureStore from "expo-secure-store";

export type ApiErrorBody = { error?: { code?: string; message?: string } };
export type Tokens = { access_token: string; refresh_token: string; token_type?: string };
export type Parent = { id: string; email: string; email_verified_at?: string | null };
export type Family = { id: string; name: string };
export type Child = { id: string; family_id: string; name: string; date_of_birth: string; age_band: string; timezone: string };
export type Pairing = { session_id: string; code: string; qr_payload: string; expires_at: string };
export type DeviceCredentials = { device_id: string; device_token: string };
export type Health = { child_profile_id: string; device_id: string; state: "PROTECTED" | "DEGRADED" | "UNKNOWN"; last_seen_at: string | null; policy_version_applied: number | null };

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://10.0.2.2:8000";
const ACCESS_TOKEN_KEY = "guardian.access-token";
const REFRESH_TOKEN_KEY = "guardian.refresh-token";
const DEVICE_TOKEN_KEY = "guardian.device-token";
const DEVICE_PRIVATE_KEY_KEY = "guardian.device-private-key";

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly code?: string) {
    super(message);
    this.name = "ApiError";
  }
}

export const sessionStorage = {
  getAccessToken: () => SecureStore.getItemAsync(ACCESS_TOKEN_KEY),
  getRefreshToken: () => SecureStore.getItemAsync(REFRESH_TOKEN_KEY),
  setTokens: async (tokens: Tokens) => {
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, tokens.access_token);
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, tokens.refresh_token);
  },
  clear: async () => {
    await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
    await SecureStore.deleteItemAsync(DEVICE_TOKEN_KEY);
    await SecureStore.deleteItemAsync(DEVICE_PRIVATE_KEY_KEY);
  },
  getDeviceToken: () => SecureStore.getItemAsync(DEVICE_TOKEN_KEY),
  setDeviceToken: (token: string) => SecureStore.setItemAsync(DEVICE_TOKEN_KEY, token),
  setDevicePrivateKey: (key: string) => SecureStore.setItemAsync(DEVICE_PRIVATE_KEY_KEY, key),
};

async function parseError(response: Response): Promise<never> {
  const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
  throw new ApiError(body.error?.message ?? "The request could not be completed.", response.status, body.error?.code);
}

export class GuardianApiClient {
  constructor(private readonly baseUrl = API_URL) {}

  private async request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
    const accessToken = await sessionStorage.getAccessToken();
    const deviceToken = await sessionStorage.getDeviceToken();
    const deviceAuthenticated = Boolean(deviceToken && path.startsWith("/v1/devices"));
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    if (deviceAuthenticated) headers.set("Authorization", `Bearer ${deviceToken}`);
    else if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
    const response = await fetch(`${this.baseUrl}${path}`, { ...init, headers });
    if (response.status === 401 && retry && accessToken && !deviceAuthenticated) {
      const refreshToken = await sessionStorage.getRefreshToken();
      if (refreshToken) {
        const refreshed = await fetch(`${this.baseUrl}/v1/auth/refresh`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: refreshToken }) });
        if (refreshed.ok) {
          await sessionStorage.setTokens((await refreshed.json()) as Tokens);
          return this.request<T>(path, init, false);
        }
      }
    }
    if (!response.ok) return parseError(response);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  signup(email: string, password: string) { return this.request<Tokens>("/v1/auth/signup", { method: "POST", body: JSON.stringify({ email, password }) }); }
  login(email: string, password: string) { return this.request<Tokens>("/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }); }
  me() { return this.request<Parent>("/v1/auth/me"); }
  createFamily(name: string) { return this.request<Family>("/v1/families", { method: "POST", body: JSON.stringify({ name }) }); }
  createChild(familyId: string, input: { name: string; date_of_birth: string; timezone: string }) { return this.request<Child>(`/v1/families/${familyId}/children`, { method: "POST", body: JSON.stringify(input) }); }
  children(familyId: string) { return this.request<Child[]>(`/v1/families/${familyId}/children`); }
  health(familyId: string) { return this.request<Health[]>(`/v1/families/${familyId}/health`); }
  createPairing(familyId: string, childId: string) { return this.request<Pairing>(`/v1/families/${familyId}/children/${childId}/pairing`, { method: "POST" }); }
  redeemPairing(input: { session_id: string; code: string; child_profile_id: string; platform: "ANDROID" | "IOS"; public_key: string }) { return this.request<DeviceCredentials>("/v1/devices/pair", { method: "POST", body: JSON.stringify(input) }); }
  policy() { return this.request<{ bundle: unknown; policy_version: number; version_mismatch: boolean }>("/v1/devices/me/policy"); }
}

export const api = new GuardianApiClient();
