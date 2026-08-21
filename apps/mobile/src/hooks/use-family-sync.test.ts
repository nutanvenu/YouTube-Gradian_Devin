import { act, renderHook } from "@testing-library/react-native";
import { sessionStorage } from "@/api/client";
import { useFamilySync } from "@/hooks/use-family-sync";

const mockInvalidateQueries = jest.fn().mockResolvedValue(undefined);

jest.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ invalidateQueries: mockInvalidateQueries }),
}));

jest.mock("@/api/client", () => ({
  api: { websocketUrl: jest.fn(() => "wss://guardian.example/v1/ws/sync?family_id=family-1") },
  sessionStorage: {
    getAccessToken: jest.fn(() => Promise.resolve("parent-token")),
    getDeviceToken: jest.fn(() => Promise.resolve(null)),
  },
}));

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  closed = false;

  constructor(
    readonly url: string,
    readonly protocols?: string | string[],
    readonly options?: { headers?: Record<string, string> },
  ) {
    MockWebSocket.instances.push(this);
  }

  send = jest.fn();

  close() {
    this.closed = true;
    this.onclose?.();
  }
}

beforeEach(() => {
  jest.useFakeTimers();
  jest.clearAllMocks();
  MockWebSocket.instances = [];
  (globalThis as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket;
  (sessionStorage.getAccessToken as jest.Mock).mockResolvedValue("parent-token");
  (sessionStorage.getDeviceToken as jest.Mock).mockResolvedValue(null);
});

afterEach(() => {
  jest.useRealTimers();
});

test("connects to the configured secure WebSocket and uses the parent bearer token", async () => {
  const hook = renderHook(() => useFamilySync("family-1", "child-1"));
  await act(async () => { await Promise.resolve(); });

  expect(MockWebSocket.instances).toHaveLength(1);
  expect(MockWebSocket.instances[0]).toMatchObject({
    url: "wss://guardian.example/v1/ws/sync?family_id=family-1",
    options: { headers: { Authorization: "Bearer parent-token" } },
  });
  hook.unmount();
});

test("falls back to polling and reconnects after a WebSocket failure", async () => {
  const hook = renderHook(() => useFamilySync("family-1"));
  await act(async () => { await Promise.resolve(); });
  const first = MockWebSocket.instances[0];

  act(() => first.onclose?.());
  expect(mockInvalidateQueries).toHaveBeenCalled();
  const callsAfterDisconnect = mockInvalidateQueries.mock.calls.length;

  act(() => jest.advanceTimersByTime(1_000));
  await act(async () => { await Promise.resolve(); });
  expect(MockWebSocket.instances).toHaveLength(2);
  act(() => MockWebSocket.instances[1].onopen?.());
  const callsAfterReconnect = mockInvalidateQueries.mock.calls.length;

  act(() => jest.advanceTimersByTime(3_000));
  expect(mockInvalidateQueries.mock.calls.length).toBe(callsAfterReconnect);

  act(() => MockWebSocket.instances[1].onclose?.());
  expect(mockInvalidateQueries.mock.calls.length).toBeGreaterThan(callsAfterDisconnect);
  act(() => jest.advanceTimersByTime(3_000));
  expect(mockInvalidateQueries.mock.calls.length).toBeGreaterThan(callsAfterReconnect);

  hook.unmount();
});
