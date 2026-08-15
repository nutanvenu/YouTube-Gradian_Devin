import { render } from "@testing-library/react-native";
import { DataState } from "@/design-system";

test.each([
  ["empty", "Nothing to show yet."],
  ["offline", "You're offline. Last-known data may be shown."],
  ["stale", "This data may be out of date."],
  ["permission-denied", "Permission is required to continue."],
  ["platform-unavailable", "This feature is unavailable on this platform."],
  ["error", "We couldn't load this data."],
  ["revoked", "Protection removed. This device is no longer linked to the family."],
  ["pending-sync", "Changes are waiting to sync."],
] as const)("renders the §31 %s state", (state, message) => {
  const screen = render(<DataState state={state}><></></DataState>);
  expect(screen.getByText(message)).toBeTruthy();
});
