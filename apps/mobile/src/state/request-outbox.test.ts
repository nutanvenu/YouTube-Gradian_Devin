import {
  enqueueRequest,
  flushRequestOutbox,
  readRequestOutbox,
  type QueuedAccessRequest,
} from "@/state/request-outbox";

test("queues a request and removes it after reconnect delivery", async () => {
  const storage = new Map<string, string>();
  const request: QueuedAccessRequest = {
    id: "local-1",
    idempotencyKey: "request-1",
    request_type: "MORE_TIME",
    subject: null,
    reason: "Please help",
    state: "QUEUED",
  };
  await enqueueRequest(request, storage);
  const delivered: string[] = [];
  await flushRequestOutbox((item) => {
    delivered.push(item.id);
    return Promise.resolve();
  }, storage);
  expect(delivered).toEqual(["local-1"]);
  expect(await readRequestOutbox(storage)).toEqual([]);
});

test("keeps a queued request terminal when its device is revoked", async () => {
  const storage = new Map<string, string>();
  await enqueueRequest(
    {
      id: "local-revoked",
      idempotencyKey: "request-revoked",
      request_type: "UNBLOCK_APP",
      subject: "com.example.app",
      reason: null,
      state: "QUEUED",
    },
    storage,
  );
  await flushRequestOutbox(() => {
    const error = new Error("Device is revoked");
    Object.assign(error, { status: 401 });
    return Promise.reject(error);
  }, storage);
  expect((await readRequestOutbox(storage))[0].state).toBe("DEVICE_REVOKED");
});
