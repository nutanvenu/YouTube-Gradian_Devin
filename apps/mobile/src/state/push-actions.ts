import { api, type AccessRequest, type RequestPushPayload } from "@/api/client";

export async function handleRequestPushAction(
  payload: RequestPushPayload,
  action: "approve" | "deny",
  reason?: string,
): Promise<AccessRequest> {
  if (payload.type !== "REQUEST_DECISION") {
    throw new Error("Unsupported push payload.");
  }
  const selected = payload.actions.find((candidate) => candidate.id === action);
  if (!selected || selected.method !== "POST") {
    throw new Error(`Push action is unavailable: ${action}`);
  }
  return api.pushAction(selected.path, reason);
}
