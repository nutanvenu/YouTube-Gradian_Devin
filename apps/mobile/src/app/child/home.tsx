import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { AppState, Text } from "react-native";
import { ApiError, api } from "@/api/client";
import { useNetworkStatus } from "@/state/network";
import {
  DataState,
  PrimaryButton,
  ProtectionRemovedState,
  ScreenScaffold,
  SectionSurface,
} from "@/design-system";
import { GuardianProtection } from "../../../modules/guardian-protection/src";
import type { GuardianNativeEvent } from "@guardian/contracts";

function isRevokedDeviceError(error: unknown): boolean {
  if (error instanceof ApiError) return error.status === 401 || error.status === 403;
  if (typeof error !== "object" || error === null || !("status" in error)) return false;
  const status = error.status;
  return status === 401 || status === 403;
}

export default function ChildHomeRoute() {
  const router = useRouter();
  const policy = useQuery({ queryKey: ["device-policy"], queryFn: () => api.policy() });
  const { isOffline } = useNetworkStatus();
  const revoked = isRevokedDeviceError(policy.error);
  const [protectionMessage, setProtectionMessage] = useState("Checking web protection…");
  const [blockedEvent, setBlockedEvent] = useState<Extract<GuardianNativeEvent, { type: "WEB_BLOCKED" }> | null>(null);
  const [blockedEventCount, setBlockedEventCount] = useState(0);

  useEffect(() => {
    const subscription = GuardianProtection.subscribe((event) => {
      if (event.type !== "WEB_BLOCKED") return;
      setBlockedEvent(event);
      setBlockedEventCount((count) => count + 1);
      console.info("GUARDIAN_BRIDGE_EVENT", JSON.stringify(event));
    });
    return () => subscription.remove();
  }, []);

  useEffect(() => {
    if (!policy.data?.bundle || revoked) return;
    let cancelled = false;
    const syncProtection = async () => {
      const result = await GuardianProtection.applyPolicyBundle(policy.data.bundle);
      if (cancelled) return;
      if (!result.applied && result.reason !== "POLICY_VERSION_NOT_MONOTONIC") {
        setProtectionMessage("Protection policy could not be applied.");
        return;
      }
      const capabilities = await GuardianProtection.getCapabilities();
      if (cancelled) return;
      if (capabilities.vpn_filtering.level !== "FULL") {
        setProtectionMessage("Web protection permission is required.");
        return;
      }
      await GuardianProtection.startProtection();
      if (!cancelled) setProtectionMessage("Web protection is active.");
    };
    void syncProtection().catch(() => {
      if (!cancelled) setProtectionMessage("Web protection is unavailable.");
    });
    const subscription = AppState.addEventListener("change", (state) => {
      if (state === "active") void syncProtection();
    });
    return () => {
      cancelled = true;
      subscription.remove();
    };
  }, [policy.data, revoked]);

  return (
    <ScreenScaffold title="My time">
      {revoked ? (
        <ProtectionRemovedState onRecover={() => router.replace("/role-selection")} />
      ) : (
        <DataState
          state={
            policy.isLoading
              ? "loading"
              : isOffline
                ? "offline"
                : policy.isError
                  ? "error"
                  : "loaded"
          }
          onRetry={() => void policy.refetch()}
        >
          <SectionSurface>
            <Text>Policy version: {policy.data?.policy_version ?? "Unknown"}</Text>
            <Text>
              {policy.data?.version_mismatch
                ? "Waiting for device acknowledgement."
                : "Policy acknowledged by this device."}
            </Text>
            <Text>{protectionMessage}</Text>
            {blockedEvent ? (
              <Text>
                WEB_BLOCKED events: {blockedEventCount} · {blockedEvent.domain} ·{" "}
                {blockedEvent.category ?? "UNKNOWN"} · {blockedEvent.reasonCode} ·{" "}
                {blockedEvent.appRef ?? "UNKNOWN_APP"}
              </Text>
            ) : null}
            {protectionMessage === "Web protection permission is required." ? (
              <PrimaryButton
                label="Enable web protection"
                onPress={() => void GuardianProtection.requestVpnPermission()}
              />
            ) : null}
          </SectionSurface>
        </DataState>
      )}
    </ScreenScaffold>
  );
}
