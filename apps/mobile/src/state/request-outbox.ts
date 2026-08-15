import * as SecureStore from "expo-secure-store";

const OUTBOX_KEY = "guardian.access-request-outbox";

export type QueuedAccessRequest = {
  id: string;
  idempotencyKey?: string;
  request_type: "MORE_TIME" | "UNBLOCK_APP" | "UNBLOCK_SITE";
  subject: string | null;
  reason: string | null;
  state: "QUEUED" | "DEVICE_REVOKED" | "FAILED";
  error?: string;
};

type Storage = Pick<typeof SecureStore, "getItemAsync" | "setItemAsync"> | Map<string, string>;

async function get(storage: Storage): Promise<string | null> {
  return storage instanceof Map
    ? storage.get(OUTBOX_KEY) ?? null
    : storage.getItemAsync(OUTBOX_KEY);
}

async function set(storage: Storage, value: string): Promise<void> {
  if (storage instanceof Map) {
    storage.set(OUTBOX_KEY, value);
  } else {
    await storage.setItemAsync(OUTBOX_KEY, value);
  }
}

export async function readRequestOutbox(
  storage: Storage = SecureStore,
): Promise<QueuedAccessRequest[]> {
  const raw = await get(storage);
  if (!raw) return [];
  try {
    const value: unknown = JSON.parse(raw);
    return Array.isArray(value) ? (value as QueuedAccessRequest[]) : [];
  } catch {
    return [];
  }
}

export async function enqueueRequest(
  request: QueuedAccessRequest,
  storage: Storage = SecureStore,
): Promise<void> {
  const queue = await readRequestOutbox(storage);
  await set(storage, JSON.stringify([...queue, request]));
}

export async function flushRequestOutbox(
  send: (request: QueuedAccessRequest) => Promise<unknown>,
  storage: Storage = SecureStore,
): Promise<QueuedAccessRequest[]> {
  const queue = await readRequestOutbox(storage);
  const remaining: QueuedAccessRequest[] = [];
  for (const request of queue) {
    try {
      await send(request);
    } catch (error) {
      const status = (error as { status?: number }).status;
      remaining.push({
        ...request,
        state: status === 401 ? "DEVICE_REVOKED" : "FAILED",
        error: error instanceof Error ? error.message : "Request delivery failed.",
      });
    }
  }
  await set(storage, JSON.stringify(remaining));
  return remaining;
}
