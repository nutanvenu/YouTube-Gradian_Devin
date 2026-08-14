import { requireNativeModule } from "expo-modules-core";
import type {
  ApplyResult,
  CapabilityRecord,
  GuardianNativeEvent,
  GuardianProtectionNative,
  ObservedApp,
  PermissionResult,
  ProtectionStatus,
  TimeRange,
  UsageSummary,
} from "@guardian/contracts";

type NativeModule = Omit<GuardianProtectionNative, "subscribe"> & {
  addListener(
    eventName: "onGuardianEvent",
    listener: (event: GuardianNativeEvent) => void,
  ): { remove: () => void };
};

const native = requireNativeModule<NativeModule>("GuardianProtection");

export const GuardianProtection: GuardianProtectionNative = {
  getCapabilities: () => native.getCapabilities(),
  getProtectionStatus: () => native.getProtectionStatus(),
  requestVpnPermission: () => native.requestVpnPermission(),
  openUsageAccessSettings: () => native.openUsageAccessSettings(),
  openAccessibilitySettings: () => native.openAccessibilitySettings(),
  openNotificationAccessSettings: () => native.openNotificationAccessSettings(),
  startProtection: () => native.startProtection(),
  applyPolicyBundle: (bundle: unknown): Promise<ApplyResult> => native.applyPolicyBundle(bundle),
  getUsageSummary: (range: TimeRange): Promise<UsageSummary> => native.getUsageSummary(range),
  getObservedApps: (): Promise<ObservedApp[]> => native.getObservedApps(),
  subscribe: (listener: (event: GuardianNativeEvent) => void) =>
    native.addListener("onGuardianEvent", listener),
};

export { type ApplyResult, type CapabilityRecord, type GuardianNativeEvent, type ObservedApp, type PermissionResult, type ProtectionStatus, type TimeRange, type UsageSummary };
