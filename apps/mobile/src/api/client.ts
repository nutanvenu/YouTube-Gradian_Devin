import * as SecureStore from "expo-secure-store";
import { signDeviceRequest } from "@/api/device-signing";

export type ApiErrorBody = { error?: { code?: string; message?: string } };
export type Tokens = { access_token: string; refresh_token: string; token_type?: string };
export type Parent = { id: string; email: string; email_verified_at?: string | null };
export type Family = { id: string; name: string };
export type Child = { id: string; family_id: string; name: string; date_of_birth: string; age_band: string; timezone: string; policy_document?: unknown };
export type Pairing = { session_id: string; code: string; qr_payload: string; expires_at: string };
export type DeviceCredentials = { device_id: string; device_token: string };
export type Health = { child_profile_id: string; device_id: string; state: "PROTECTED" | "DEGRADED" | "UNKNOWN"; last_seen_at: string | null; policy_version_applied: number | null };
export type PolicyMutationInput = {
  operation:
    | "APP_ALLOW"
    | "APP_BLOCK"
    | "APP_UNLIMITED"
    | "APP_DAILY_MINUTES"
    | "APP_SCHEDULE"
    | "DOMAIN_ALLOW"
    | "DOMAIN_BLOCK"
    | "CATEGORY_DAILY_MINUTES"
    | "WEB_CATEGORY_ALLOW"
    | "WEB_CATEGORY_BLOCK"
    | "UNKNOWN_DOMAIN_POLICY"
    | "UNKNOWN_APP_POLICY"
    | "ROUTINE_CREATE"
    | "ROUTINE_UPDATE"
    | "ROUTINE_DELETE"
    | "ROUTINE_ACTIVATE"
    | "ROUTINE_DEACTIVATE";
  target: string;
  value?: unknown;
  expires_at?: string;
};
export type PolicyMutation = {
  bundle: unknown;
  policy_version: number;
  effective_at: string;
  expires_at: string | null;
};
export type AccessRequest = {
  id: string;
  child_profile_id: string;
  device_id: string;
  request_type: "MORE_TIME" | "UNBLOCK_APP" | "UNBLOCK_SITE";
  subject: string | null;
  state: "PENDING" | "APPROVED" | "DENIED" | "EXPIRED" | "CANCELLED";
  reason: string | null;
  decision_reason: string | null;
  expires_at: string | null;
};
export type ActivityEvent = {
  id: string;
  kind: "WEB" | "SAFETY";
  event_type: string;
  occurred_at: string;
  domain: string | null;
  app_ref: string | null;
};

const configuredApiUrl = typeof process.env.EXPO_PUBLIC_API_URL === "string"
  ? process.env.EXPO_PUBLIC_API_URL.replace(/\/+$/, "")
  : undefined;
const API_URL = configuredApiUrl ?? (__DEV__ ? "http://10.0.2.2:8000" : "https://api.guardian.example");
if (!__DEV__ && !API_URL.startsWith("https://")) {
  throw new Error("Release builds require an HTTPS API URL.");
}
const ACCESS_TOKEN_KEY = "guardian.access-token";
const REFRESH_TOKEN_KEY = "guardian.refresh-token";
const DEVICE_TOKEN_KEY = "guardian.device-token";
const DEVICE_PRIVATE_KEY_KEY = "guardian.device-private-key";
const FAMILY_ID_KEY = "guardian.family-id";

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
    await SecureStore.deleteItemAsync(FAMILY_ID_KEY);
  },
  getDeviceToken: () => SecureStore.getItemAsync(DEVICE_TOKEN_KEY),
  setDeviceToken: (token: string) => SecureStore.setItemAsync(DEVICE_TOKEN_KEY, token),
  setDevicePrivateKey: (key: string) => SecureStore.setItemAsync(DEVICE_PRIVATE_KEY_KEY, key),
  getFamilyId: () => SecureStore.getItemAsync(FAMILY_ID_KEY),
  setFamilyId: (familyId: string) => SecureStore.setItemAsync(FAMILY_ID_KEY, familyId),
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
    if (deviceAuthenticated && init.method && init.method !== "GET") {
      const privateKey = await SecureStore.getItemAsync(DEVICE_PRIVATE_KEY_KEY);
      if (!privateKey) throw new ApiError("Device proof is unavailable.", 401, "DEVICE_PROOF_MISSING");
      const timestamp = String(Math.floor(Date.now() / 1000));
      const nonce = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const body = typeof init.body === "string" ? init.body : "";
      headers.set("X-Guardian-Device-Timestamp", timestamp);
      headers.set("X-Guardian-Device-Nonce", nonce);
      headers.set(
        "X-Guardian-Device-Signature",
        await signDeviceRequest(privateKey, init.method, path, timestamp, nonce, body),
      );
    }
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
  families() { return this.request<Family[]>("/v1/families"); }
  createChild(familyId: string, input: { name: string; date_of_birth: string; timezone: string }) { return this.request<Child>(`/v1/families/${familyId}/children`, { method: "POST", body: JSON.stringify(input) }); }
  children(familyId: string) { return this.request<Child[]>(`/v1/families/${familyId}/children`); }
  health(familyId: string) { return this.request<Health[]>(`/v1/families/${familyId}/health`); }
  activity(familyId: string) { return this.request<ActivityEvent[]>(`/v1/families/${familyId}/activity`); }
  createPairing(familyId: string, childId: string) { return this.request<Pairing>(`/v1/families/${familyId}/children/${childId}/pairing`, { method: "POST" }); }
  redeemPairing(input: { session_id: string; code: string; child_profile_id: string; platform: "ANDROID" | "IOS"; public_key: string }) { return this.request<DeviceCredentials>("/v1/devices/pair", { method: "POST", body: JSON.stringify(input) }); }
  policy() { return this.request<{ bundle: unknown; policy_version: number; version_mismatch: boolean }>("/v1/devices/me/policy"); }
  acknowledgePolicy(policyVersion: number) {
    return this.request<undefined>("/v1/devices/me/policy/ack", {
      method: "POST",
      body: JSON.stringify({ policy_version: policyVersion }),
    });
  }
  heartbeat(body: { protection_state: "HEALTHY" | "DEGRADED" | "DISABLED" | "UNKNOWN"; capabilities: unknown }) {
    return this.request<undefined>("/v1/devices/me/heartbeat", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }
  mutatePolicy(familyId: string, childId: string, input: PolicyMutationInput) {
    return this.request<PolicyMutation>(`/v1/families/${familyId}/children/${childId}/policy/mutations`, {
      method: "POST",
      headers: { "Idempotency-Key": `${input.operation}:${input.target}:${Date.now()}` },
      body: JSON.stringify(input),
    });
  }
  createRequest(input: Omit<AccessRequest, "id" | "child_profile_id" | "device_id" | "state" | "decision_reason" | "expires_at">, idempotencyKey?: string) {
    return this.request<AccessRequest>("/v1/devices/me/requests", {
      method: "POST",
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
      body: JSON.stringify(input),
    });
  }
  requests(familyId: string) {
    return this.request<AccessRequest[]>(`/v1/families/${familyId}/requests`);
  }
  decideRequest(familyId: string, requestId: string, decision: "approve" | "deny", reason: string) {
    return this.request<AccessRequest>(`/v1/families/${familyId}/requests/${requestId}/${decision}`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }
  websocketUrl(path: string, params: Record<string, string>) {
    const url = new URL(`${this.baseUrl}${path}`);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
    return url.toString();
  }
}

export const api = new GuardianApiClient();
