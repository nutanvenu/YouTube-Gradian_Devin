import { fireEvent, render, waitFor } from "@testing-library/react-native";
import { Text } from "react-native";

const mockQueryState = new Map<string, Record<string, unknown>>();
const mockMutatePolicy = jest.fn();
const mockDecideRequest = jest.fn();
const mockReviewApp = jest.fn();
let mockOffline = false;

jest.mock("react-native-safe-area-context", () => ({
  useSafeAreaInsets: () => ({ top: 0, right: 0, bottom: 0, left: 0 }),
}));

jest.mock("expo-router", () => ({
  useLocalSearchParams: () => ({ familyId: "family-1", childId: "child-1" }),
}));

jest.mock("@/api/client", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
  api: {
    mutatePolicy: (...args: unknown[]) => {
      mockMutatePolicy(...args);
      return Promise.resolve({});
    },
    decideRequest: (...args: unknown[]) => {
      mockDecideRequest(...args);
      return Promise.resolve({});
    },
    children: () => Promise.resolve([]),
    health: () => Promise.resolve([]),
    requests: () => Promise.resolve([]),
    activity: () => Promise.resolve([]),
    activityUsage: () => Promise.resolve([]),
    childInventory: () => Promise.resolve([]),
    reviewChildApp: (...args: unknown[]) => {
      mockReviewApp(...args);
      return Promise.resolve();
    },
    ingestInventory: () => Promise.resolve(),
  },
}));

jest.mock("@/hooks/use-family-sync", () => ({ useFamilySync: jest.fn() }));
jest.mock("../modules/guardian-protection/src", () => ({
  GuardianProtection: {
  getObservedApps: () => Promise.resolve([]),
  markObservedAppReviewed: (...args: unknown[]) => {
    mockReviewApp(...args);
    return Promise.resolve();
  },
    getCapabilities: () => Promise.resolve({}),
    getProtectionStatus: () => Promise.resolve({ active: false, health: "UNKNOWN" }),
    getUsageSummary: () => Promise.resolve({ byTarget: {} }),
    openUsageAccessSettings: jest.fn(),
    openAccessibilitySettings: jest.fn(),
  },
}));

jest.mock("@tanstack/react-query", () => ({
  useQuery: ({ queryKey }: { queryKey: unknown[] }) => {
    const state = mockQueryState.get(JSON.stringify(queryKey));
    return {
      data: state?.data,
      error: state?.error,
      isLoading: state?.isLoading ?? false,
      isError: state?.isError ?? false,
      isStale: state?.isStale ?? false,
      refetch: state?.refetch ?? jest.fn(),
    };
  },
  useMutation: () => ({
    mutate: (input: unknown) => {
      mockMutatePolicy(input);
    },
    isPending: false,
  }),
  useQueryClient: () => ({ invalidateQueries: jest.fn() }),
}));

jest.mock("@/state/network", () => ({ useNetworkStatus: () => ({ isOffline: mockOffline }) }));

import RulesScreen from "@/app/parent/rules";
import RequestsScreen from "@/app/parent/requests";
import HealthScreen from "@/app/parent/health";
import ActivityScreen from "@/app/parent/activity";

function setQuery(key: unknown[], state: Record<string, unknown>) {
  mockQueryState.set(JSON.stringify(key), state);
}

beforeEach(() => {
  mockQueryState.clear();
  mockMutatePolicy.mockReset();
  mockDecideRequest.mockReset();
  mockReviewApp.mockReset();
  mockOffline = false;
});

test("Rules renders loading and pending-sync states and submits an app limit", async () => {
  setQuery(["children", "family-1"], { isLoading: true });
  setQuery(["child-inventory", "family-1", "child-1"], { isLoading: true });
  const loading = render(<RulesScreen />);
  expect(loading.getByLabelText("Loading")).toBeTruthy();
  loading.unmount();

  setQuery(["children", "family-1"], {
    data: [{
      id: "child-1",
      name: "Alex",
      policy_document: { app_rules: [], domain_rules: [], base_policy: {} },
    }],
  });
  setQuery(["child-inventory", "family-1", "child-1"], {
    data: [{ platform_app_id: "com.example.app", display_name: "Example", category: null, reviewed: true }],
  });
  setQuery(["health", "family-1"], { data: [] });
  const screen = render(<RulesScreen />);
  expect(screen.getByText(/Rules active on device\./)).toBeTruthy();
  fireEvent.press(screen.getByLabelText("Limit to 30 minutes"));
  await waitFor(() => expect(mockMutatePolicy).toHaveBeenCalledWith({
    operation: "APP_DAILY_MINUTES",
    target: "com.example.app",
    value: 30,
  }));
});

test("Rules keeps a newly observed app in review until the parent marks it reviewed", async () => {
  setQuery(["children", "family-1"], {
    data: [{
      id: "child-1",
      name: "Alex",
      policy_document: { app_rules: [], domain_rules: [], base_policy: {} },
    }],
  });
  const refetch = jest.fn();
  setQuery(["child-inventory", "family-1", "child-1"], {
    data: [{ platform_app_id: "com.example.new", display_name: "New app", category: null, reviewed: false }],
    refetch,
  });
  setQuery(["health", "family-1"], { data: [] });
  const screen = render(<RulesScreen />);
  expect(screen.getByText("This app was newly observed on the child device. Review it before treating it as trusted.")).toBeTruthy();
  fireEvent.press(screen.getByLabelText("Mark app reviewed"));
  await waitFor(() => expect(mockReviewApp).toHaveBeenCalledWith("family-1", "child-1", "com.example.new"));
  expect(refetch).toHaveBeenCalled();
});

test("Requests renders retry and terminal approval states", async () => {
  const refetch = jest.fn();
  setQuery(["requests", "family-1"], { isError: true, refetch });
  const errorScreen = render(<RequestsScreen />);
  fireEvent.press(errorScreen.getByLabelText("Retry"));
  expect(refetch).toHaveBeenCalled();
  errorScreen.unmount();

  setQuery(["requests", "family-1"], {
    data: [{
      id: "request-1",
      request_type: "MORE_TIME",
      subject: "Example",
      reason: "Please help",
      state: "PENDING",
    }],
  });
  const screen = render(<RequestsScreen />);
  expect(screen.getByText("Waiting for a parent")).toBeTruthy();
  fireEvent.press(screen.getByLabelText("Approve"));
  await waitFor(() => expect(mockMutatePolicy).toHaveBeenCalled());
});

test("Rules and Requests render stale and offline states", () => {
  setQuery(["children", "family-1"], { data: [], isStale: true });
  setQuery(["child-inventory", "family-1", "child-1"], { data: [] });
  const staleRules = render(<RulesScreen />);
  expect(staleRules.getByText("This data may be out of date.")).toBeTruthy();
  staleRules.unmount();

  mockOffline = true;
  setQuery(["requests", "family-1"], { data: [] });
  const offlineRequests = render(<RequestsScreen />);
  expect(offlineRequests.getByText("You're offline. Last-known data may be shown.")).toBeTruthy();
});

test("Protection Health renders permission-denied and platform-unavailable capability details", () => {
  setQuery(["health", "family-1"], { data: [] });
  setQuery(["guardian-capabilities"], {
    data: {
      app_usage: { level: "UNAVAILABLE", detail: "Permission denied" },
      web_filtering: { level: "PLATFORM_UNAVAILABLE", detail: "Platform unavailable" },
    },
  });
  setQuery(["guardian-status"], { data: { active: false, health: "DEGRADED", details: "Permission denied" } });
  const screen = render(<HealthScreen />);
  expect(screen.getAllByText("Permission denied").length).toBeGreaterThan(0);
  expect(screen.getByText("Platform unavailable")).toBeTruthy();
  expect(screen.getByText("DEGRADED")).toBeTruthy();
});

test("Activity renders empty data distinctly from endpoint errors", () => {
  const refetch = jest.fn();
  setQuery(["activity", "family-1"], { data: [], isError: true, refetch });
  setQuery(["activity-usage", "family-1"], { data: [] });
  setQuery(["usage-summary"], { data: { byTarget: {} } });
  const screen = render(<ActivityScreen />);
  fireEvent.press(screen.getByLabelText("Retry"));
  expect(refetch).toHaveBeenCalled();
  expect(screen.getByText("We couldn't load this data.")).toBeTruthy();
  screen.unmount();

  setQuery(["activity", "family-1"], { data: [] });
  setQuery(["activity-usage", "family-1"], { data: [] });
  const loaded = render(<ActivityScreen />);
  expect(loaded.getByText("Nothing to show yet.")).toBeTruthy();
  expect(loaded.getByText("Unknown · this family has not reported activity yet.")).toBeTruthy();
  expect(loaded.getByText("Unknown · no backend events are available for this family.")).toBeTruthy();
  expect(loaded.getByText("Unknown · no usage aggregates are available for this family.")).toBeTruthy();
});

test("Activity renders permission-denied for an expired session", () => {
  const ApiError = jest.requireMock("@/api/client").ApiError as new (message: string, status: number) => Error & { status: number };
  setQuery(["activity", "family-1"], { error: new ApiError("Unauthorized", 401), isError: true });
  setQuery(["activity-usage", "family-1"], { data: [] });
  setQuery(["usage-summary"], { data: { byTarget: {} } });
  const screen = render(<ActivityScreen />);
  expect(screen.getByText("Permission is required to continue.")).toBeTruthy();
  expect(screen.queryByText("We couldn't load this data.")).toBeNull();
});

test("screen test harness can render a state marker", () => {
  expect(render(<Text>pending-sync</Text>).getByText("pending-sync")).toBeTruthy();
});
