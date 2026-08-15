import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, sessionStorage } from "@/api/client";

export function useFamilySync(familyId: string | undefined, childId?: string) {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!familyId) return;
    let socket: WebSocket | null = null;
    let cancelled = false;
    const connect = async () => {
      const token =
        (await sessionStorage.getAccessToken()) ??
        (await sessionStorage.getDeviceToken());
      if (cancelled || !token) return;
      const WebSocketWithHeaders = WebSocket as unknown as new (
        url: string,
        protocols?: string | string[],
        options?: { headers?: Record<string, string> },
      ) => WebSocket;
      socket = new WebSocketWithHeaders(
        api.websocketUrl("/v1/ws/sync", {
          family_id: familyId,
          ...(childId ? { child_profile_id: childId } : {}),
        }),
        undefined,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      socket.onmessage = ({ data }) => {
        const event = JSON.parse(String(data)) as { type?: string };
        if (event.type === "ping") {
          socket?.send("pong");
          return;
        }
        void Promise.all([
          queryClient.invalidateQueries({ queryKey: ["children", familyId] }),
          queryClient.invalidateQueries({ queryKey: ["health", familyId] }),
          queryClient.invalidateQueries({ queryKey: ["requests", familyId] }),
          queryClient.invalidateQueries({ queryKey: ["activity", familyId] }),
          queryClient.invalidateQueries({ queryKey: ["device-policy"] }),
        ]).catch(() => undefined);
      };
    };
    void connect().catch(() => undefined);
    return () => {
      cancelled = true;
      socket?.close();
    };
  }, [childId, familyId, queryClient]);
}
