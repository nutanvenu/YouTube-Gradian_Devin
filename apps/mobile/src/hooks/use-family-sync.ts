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
      const token = await sessionStorage.getAccessToken();
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
        void queryClient.invalidateQueries({ queryKey: ["children", familyId] });
        void queryClient.invalidateQueries({ queryKey: ["health", familyId] });
        void queryClient.invalidateQueries({ queryKey: ["requests", familyId] });
        void queryClient.invalidateQueries({ queryKey: ["activity", familyId] });
        void queryClient.invalidateQueries({ queryKey: ["device-policy"] });
      };
    };
    void connect();
    return () => {
      cancelled = true;
      socket?.close();
    };
  }, [childId, familyId, queryClient]);
}
