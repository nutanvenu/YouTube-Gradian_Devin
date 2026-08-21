import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, sessionStorage } from "@/api/client";

const POLL_INTERVAL_MS = 3_000;
const INITIAL_RECONNECT_DELAY_MS = 1_000;
const MAX_RECONNECT_DELAY_MS = 30_000;

export function useFamilySync(familyId: string | undefined, childId?: string) {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!familyId) return;
    let socket: WebSocket | null = null;
    let cancelled = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectDelay = INITIAL_RECONNECT_DELAY_MS;

    const invalidateFamilyQueries = () => Promise.all([
      queryClient.invalidateQueries({ queryKey: ["children", familyId] }),
      queryClient.invalidateQueries({ queryKey: ["health", familyId] }),
      queryClient.invalidateQueries({ queryKey: ["requests", familyId] }),
      queryClient.invalidateQueries({ queryKey: ["activity", familyId] }),
      queryClient.invalidateQueries({ queryKey: ["device-policy"] }),
    ]).catch(() => undefined);

    const stopPolling = () => {
      if (pollTimer !== null) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    // WebSockets are the low-latency path, but some consumer networks and
    // proxies reject upgrades. Polling keeps parent requests and policy state
    // honest without pretending the socket is connected.
    const startPolling = () => {
      if (pollTimer !== null || cancelled) return;
      void invalidateFamilyQueries();
      pollTimer = setInterval(() => void invalidateFamilyQueries(), POLL_INTERVAL_MS);
    };

    const scheduleReconnect = () => {
      if (cancelled) return;
      startPolling();
      if (reconnectTimer !== null) return;
      const delay = reconnectDelay;
      reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY_MS);
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        void connect().catch(scheduleReconnect);
      }, delay);
    };

    const connect = async () => {
      const token =
        (await sessionStorage.getAccessToken()) ??
        (await sessionStorage.getDeviceToken());
      if (cancelled || !token) {
        if (!cancelled) scheduleReconnect();
        return;
      }
      const WebSocketWithHeaders = WebSocket as unknown as new (
        url: string,
        protocols?: string | string[],
        options?: { headers?: Record<string, string> },
      ) => WebSocket;
      const currentSocket = new WebSocketWithHeaders(
        api.websocketUrl("/v1/ws/sync", {
          family_id: familyId,
          ...(childId ? { child_profile_id: childId } : {}),
        }),
        undefined,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      socket = currentSocket;
      currentSocket.onopen = () => {
        reconnectDelay = INITIAL_RECONNECT_DELAY_MS;
        stopPolling();
      };
      currentSocket.onmessage = ({ data }) => {
        const event = JSON.parse(String(data)) as { type?: string };
        if (event.type === "ping") {
          currentSocket.send("pong");
          return;
        }
        void invalidateFamilyQueries();
      };
      currentSocket.onerror = () => {
        if (!cancelled) currentSocket.close();
      };
      currentSocket.onclose = () => {
        if (!cancelled) scheduleReconnect();
      };
    };
    void connect().catch(scheduleReconnect);
    return () => {
      cancelled = true;
      stopPolling();
      if (reconnectTimer !== null) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [childId, familyId, queryClient]);
}
