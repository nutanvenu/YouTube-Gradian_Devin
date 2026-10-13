import { act, fireEvent, render, waitFor } from "@testing-library/react-native";

const mockQueryState = new Map<string, Record<string, unknown>>();
const mockMutatePolicy = jest.fn();
const mockDecideRequest = jest.fn();
const mockPush = jest.fn();
let mockParams: Record<string, string> = {
  familyId: "family-1",
  childId: "child-1",
  routineId: "routine-1",
  requestId: "request-1",
  appId: "com.example.school",
};

jest.mock("react-native-safe-area-context", () => ({
  useSafeAreaInsets: () => ({ top: 0, right: 0, bottom: 0, left: 0 }),
}));

jest.mock("expo-router", () => ({
  useLocalSearchParams: () => mockParams,
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("expo-crypto", () => ({ randomUUID: () => "routine-new" }));

jest.mock("@/auth/session", () => ({
  useSession: () => ({
    familyId: "family-1",
    childId: null,
    setChildId: jest.fn(),
    signOut: jest.fn(),
    sessionError: null,
  }),
}));

jest.mock("@/state/network", () => ({ useNetworkStatus: () => ({ isOffline: false }) }));

jest.mock("@/api/client", () => ({
  api: {
    child: jest.fn(),
    children: jest.fn(),
    family: jest.fn(),
    guardians: jest.fn(),
    health: jest.fn(),
    activityUsage: jest.fn(),
    requests: jest.fn(),
    policy: jest.fn(),
    mutatePolicy: (...args: unknown[]) => {
      mockMutatePolicy(...args);
      return Promise.resolve({ policy_version: 5 });
    },
    decideRequest: (...args: unknown[]) => {
      mockDecideRequest(...args);
      return Promise.resolve({});
    },
  },
}));

jest.mock("@tanstack/react-query", () => ({
  useQuery: ({ queryKey }: { queryKey: unknown[] }) => {
    const state = mockQueryState.get(JSON.stringify(queryKey));
    return {
      data: state?.data,
      isLoading: state?.isLoading ?? false,
      isError: state?.isError ?? false,
      refetch: state?.refetch ?? jest.fn(),
    };
  },
  useMutation: ({ mutationFn, onSuccess }: { mutationFn: (input: unknown) => Promise<unknown>; onSuccess?: (result: unknown, input: unknown) => void }) => ({
    mutate: (input: unknown) => {
      void mutationFn(input).then((result) => onSuccess?.(result, input));
    },
    isPending: false,
  }),
  useQueryClient: () => ({ invalidateQueries: jest.fn() }),
}));

import ActivityDetailRoute from "@/app/parent/activity-detail";
import ParentHomeRoute from "@/app/parent/home";
import ChildDetailRoute from "@/app/parent/child-detail";
import FamilySettingsRoute from "@/app/parent/family-settings";
import GuardianDeviceSettingsRoute from "@/app/parent/guardian-device-settings";
import HelpRoute from "@/app/parent/help";
import NotificationSettingsRoute from "@/app/parent/notification-settings";
import RequestDetailRoute from "@/app/parent/request-detail";
import RoutineEditorRoute from "@/app/parent/routine-editor";
import ChildRulesSummaryRoute from "@/app/child/rules-summary";
import ChildTimeUpRoute from "@/app/child/time-up";

function setQuery(key: unknown[], state: Record<string, unknown>) {
  mockQueryState.set(JSON.stringify(key), state);
}

const child = {
  id: "child-1",
  name: "Alex",
  age_band: "B",
  timezone: "UTC",
  policy_document: {
    routines: [{ routine_id: "routine-1", name: "Homework", kind: "SCHEDULED" }],
  },
};

const health = [{
  child_profile_id: "child-1",
  device_id: "device-1",
  state: "PROTECTED",
  policy_version_applied: 4,
  last_seen_at: "2026-01-01T00:00:00Z",
}];

const activity = [{
  app_ref: "com.example.school",
  category: "EDUCATION",
  duration_seconds: 1800,
  occurred_at: "2026-01-01T00:00:00Z",
}];

const request = {
  id: "request-1",
  request_type: "MORE_TIME",
  state: "PENDING",
  subject: "Homework",
  reason: "Please help",
};

beforeEach(() => {
  mockQueryState.clear();
  mockMutatePolicy.mockReset();
  mockDecideRequest.mockReset();
  mockPush.mockReset();
  mockParams = {
    familyId: "family-1",
    childId: "child-1",
    routineId: "routine-1",
    requestId: "request-1",
    appId: "com.example.school",
  };
});

function setLoadedQueries() {
  setQuery(["child", "family-1", "child-1"], { data: child });
  setQuery(["children", "family-1"], { data: [child] });
  setQuery(["family", "family-1"], { data: { id: "family-1", name: "Guardian family" } });
  setQuery(["guardians", "family-1"], { data: [{ id: "guardian-1", parent_id: "parent-1", role: "OWNER" }] });
  setQuery(["health", "family-1", "child-1"], { data: health });
  setQuery(["activity-usage", "family-1", "child-1"], { data: activity });
  setQuery(["requests", "family-1", "child-1"], { data: [request] });
  setQuery(["device-policy"], {
    data: {
      bundle: {
        base_policy: { unknown_app_policy: "BLOCK", unknown_domain_policy: "BLOCK" },
        app_rules: [{ rule_id: "app-1", app_ref: "com.example.school", action: "ALLOW" }],
        category_rules: [{ rule_id: "category-1", category: "EDUCATION", action: "ALLOW" }],
      },
    },
  });
}

test("Parent can add a child when its family has no child profiles", () => {
  setQuery(["children", "family-1"], { data: [] });
  const screen = render(<ParentHomeRoute />);
  expect(screen.getByText("Nothing to show yet.")).toBeTruthy();
  fireEvent.press(screen.getByLabelText("Add a child"));
  expect(mockPush).toHaveBeenCalledWith({ pathname: "/parent/setup", params: { familyId: "family-1" } });
});

test("new parent and child routes render loaded data", () => {
  setLoadedQueries();

  const routes = [
    [ChildDetailRoute, "Child detail", "Alex"],
    [ActivityDetailRoute, "App activity detail", "com.example.school"],
    [RoutineEditorRoute, "Routine editor", "Homework"],
    [RequestDetailRoute, "Request detail", "Approve request"],
    [FamilySettingsRoute, "Family settings", "Guardian family"],
    [GuardianDeviceSettingsRoute, "Guardian and device settings", "OWNER"],
    [NotificationSettingsRoute, "Notification settings", "Backend action payloads enabled"],
    [HelpRoute, "Help and troubleshooting", "device-1: PROTECTED"],
    [ChildRulesSummaryRoute, "My simple rules", "Unknown apps"],
  ] as const;

  for (const [Route, title, content] of routes) {
    const screen = render(<Route />);
    expect(screen.getByText(title)).toBeTruthy();
    expect(screen.getAllByText(new RegExp(content)).length).toBeGreaterThan(0);
    screen.unmount();
  }
});

test("new routes expose loading, error, and empty states with recovery", () => {
  const refetch = jest.fn();
  setQuery(["child", "family-1", "child-1"], { isLoading: true });
  setQuery(["health", "family-1", "child-1"], { isLoading: true });
  const loading = render(<ChildDetailRoute />);
  expect(loading.getByLabelText("Loading")).toBeTruthy();
  loading.unmount();

  setQuery(["activity-usage", "family-1", "child-1"], { isError: true, refetch });
  const error = render(<ActivityDetailRoute />);
  expect(error.getByText("We couldn't load this data.")).toBeTruthy();
  fireEvent.press(error.getByLabelText("Retry"));
  expect(refetch).toHaveBeenCalled();
  error.unmount();

  setQuery(["requests", "family-1", "child-1"], { data: [] });
  const empty = render(<RequestDetailRoute />);
  expect(empty.getByText("Nothing to show yet.")).toBeTruthy();
});

test("new route actions navigate and submit policy/request decisions", async () => {
  setLoadedQueries();

  const timeUp = render(<ChildTimeUpRoute />);
  fireEvent.press(timeUp.getByLabelText("Ask for more time"));
  expect(mockPush).toHaveBeenCalledWith("/child/requests");
  timeUp.unmount();

  const routine = render(<RoutineEditorRoute />);
  expect(routine.queryByLabelText("Activate routine")).toBeNull();
  fireEvent.changeText(routine.getByLabelText("Routine name"), "Study time");
  await act(async () => {
    fireEvent.press(routine.getByLabelText("Save routine"));
    await Promise.resolve();
  });
  expect(mockMutatePolicy).toHaveBeenCalledWith(
    "family-1",
    "child-1",
    expect.objectContaining({ operation: "ROUTINE_UPDATE", target: "routine-1", value: expect.objectContaining({ name: "Study time", kind: "SCHEDULED" }) }),
  );
  routine.unmount();

  const requestDetail = render(<RequestDetailRoute />);
  fireEvent.press(requestDetail.getByLabelText("Approve request"));
  expect(mockDecideRequest).toHaveBeenCalledWith(
    "family-1",
    "request-1",
    "approve",
    "Reviewed in request detail",
  );
});

test("creates a manual routine and can activate it after saving", async () => {
  setLoadedQueries();
  delete mockParams.routineId;
  const editor = render(<RoutineEditorRoute />);
  fireEvent.press(editor.getByLabelText("Switch to manual"));
  expect(editor.queryByLabelText("Activate routine")).toBeNull();
  fireEvent.press(editor.getByLabelText("Save routine"));
  await waitFor(() => expect(editor.getByLabelText("Activate routine")).toBeTruthy());
  expect(mockMutatePolicy).toHaveBeenCalledWith("family-1", "child-1", expect.objectContaining({
    operation: "ROUTINE_CREATE", target: "routine-new",
    value: expect.objectContaining({ routine_id: "routine-new", kind: "MANUAL" }),
  }));
  await act(async () => {
    fireEvent.press(editor.getByLabelText("Activate routine"));
    await Promise.resolve();
  });
  expect(mockMutatePolicy).toHaveBeenLastCalledWith("family-1", "child-1", { operation: "ROUTINE_ACTIVATE", target: "routine-new" });
});

test("invalid routine drafts show a correction without submitting", () => {
  setLoadedQueries();
  const editor = render(<RoutineEditorRoute />);
  fireEvent.changeText(editor.getByLabelText("Routine name"), " ");
  fireEvent.press(editor.getByLabelText("Save routine"));
  expect(editor.getByText("Enter a routine name.")).toBeTruthy();
  expect(mockMutatePolicy).not.toHaveBeenCalled();
});
