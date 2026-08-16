import { render, screen, waitFor } from "@testing-library/react-native";
import { Text } from "react-native";

jest.mock("@/api/client", () => {
  class MockApiError extends Error {
    constructor(message: string, mockStatus: number, mockCode?: string) {
      super(message);
      this.name = "ApiError";
      Object.assign(this, { status: mockStatus, code: mockCode });
    }
  }
  return {
    ApiError: MockApiError,
    api: { me: jest.fn(), families: jest.fn() },
    sessionStorage: {
      getAccessToken: jest.fn(),
      getFamilyId: jest.fn(),
      clearParentSession: jest.fn(),
      setFamilyId: jest.fn(),
      setTokens: jest.fn(),
    },
    subscribeToParentSessionExpiry: jest.fn(() => () => undefined),
  };
});

import { ApiError, api, sessionStorage } from "@/api/client";
import { SessionProvider, useSession } from "@/auth/session";

function SessionState() {
  const { loading, sessionError } = useSession();
  return <Text>{loading ? "loading" : sessionError ?? "clear"}</Text>;
}

beforeEach(() => {
  jest.clearAllMocks();
  (sessionStorage.getAccessToken as jest.Mock).mockResolvedValue("expired-access");
  (sessionStorage.getFamilyId as jest.Mock).mockResolvedValue("family-1");
  (sessionStorage.clearParentSession as jest.Mock).mockResolvedValue(undefined);
});

test("bootstrap preserves SESSION_EXPIRED as an actionable signed-out state", async () => {
  (api.me as jest.Mock).mockRejectedValue(new ApiError("Session expired", 401, "SESSION_EXPIRED"));

  render(<SessionProvider><SessionState /></SessionProvider>);

  await waitFor(() => expect(screen.getByText("SESSION_EXPIRED")).toBeTruthy());
  expect(sessionStorage.clearParentSession).toHaveBeenCalledTimes(1);
});
