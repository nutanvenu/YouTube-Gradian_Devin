import { api } from "@/api/client";
import { handleRequestPushAction } from "@/state/push-actions";

jest.mock("@/api/device-signing", () => ({
  signDeviceRequest: jest.fn(),
}));

const mockPushAction = jest.spyOn(api, "pushAction");

beforeEach(() => {
  mockPushAction.mockReset();
});

test("routes notification approve action to the server action path", async () => {
  const request = {
    id: "request-1",
    child_profile_id: "child-1",
    device_id: "device-1",
    request_type: "MORE_TIME" as const,
    subject: "Chrome",
    state: "APPROVED" as const,
    reason: "Homework",
    decision_reason: "Approved",
    expires_at: null,
  };
  mockPushAction.mockResolvedValue(request);
  const payload = {
    type: "REQUEST_DECISION" as const,
    request_id: "request-1",
    title: "Guardian request",
    body: "Approve?",
    actions: [
      { id: "approve" as const, label: "Approve", method: "POST" as const, path: "/v1/push/actions/a/approve" },
      { id: "deny" as const, label: "Deny", method: "POST" as const, path: "/v1/push/actions/d/deny" },
    ],
  };
  await expect(handleRequestPushAction(payload, "approve", "Approved in notification")).resolves.toEqual(request);
  expect(mockPushAction).toHaveBeenCalledWith("/v1/push/actions/a/approve", "Approved in notification");
});

test("rejects malformed notification actions before making a request", async () => {
  const payload = {
    type: "REQUEST_DECISION" as const,
    request_id: "request-1",
    title: "Guardian request",
    body: "Approve?",
    actions: [],
  };
  await expect(handleRequestPushAction(payload, "deny")).rejects.toThrow("Push action is unavailable");
  expect(mockPushAction).not.toHaveBeenCalled();
});
