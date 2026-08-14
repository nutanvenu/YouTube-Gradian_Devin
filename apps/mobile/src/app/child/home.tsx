import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { AppState, Text } from "react-native";
import { ApiError, api, sessionStorage } from "@/api/client";
import { useFamilySync } from "@/hooks/use-family-sync";
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
  const [familyId, setFamilyId] = useState<string>();
  const revoked = isRevokedDeviceError(policy.error);
  const [protectionMessage, setProtectionMessage] = useState("Checking web protection…");
  const [blockedEvent, setBlockedEvent] = useState<Extract<GuardianNativeEvent, { type: "WEB_BLOCKED" }> | null>(null);
  const [blockedEventCount, setBlockedEventCount] = useState(0);
  const [appBlockedMessage, setAppBlockedMessage] = useState<string | null>(null);
  const [timeMessage, setTimeMessage] = useState<string | null>(null);
  const [acknowledgedVersion, setAcknowledgedVersion] = useState<number | null>(null);
  const usageUploaded = useRef(false);

  useEffect(() => {
    let mounted = true;
    void sessionStorage.getFamilyId().then((value) => {
      if (mounted) setFamilyId(value ?? undefined);
    });
    return () => {
      mounted = false;
    };
  }, []);

  useFamilySync(familyId);

  useEffect(() => {
    const subscription = GuardianProtection.subscribe((event) => {
      if (event.type === "WEB_BLOCKED") {
        setBlockedEvent(event);
        setBlockedEventCount((count) => count + 1);
        void api.ingestEvents([{
          event_type: event.type,
          occurred_at: new Date().toISOString(),
          app_ref: event.appRef ?? null,
          domain: event.domain,
          category: event.category ?? null,
        }]).catch(() => undefined);
      }
      console.info("GUARDIAN_BRIDGE_EVENT", JSON.stringify(event));
      if (event.type === "APP_BLOCKED") {
        setAppBlockedMessage(`${event.appRef} · ${event.reasonCode}`);
      }
      if (event.type === "TIME_WARNING") {
        setTimeMessage(`${event.targetRef} · ${event.remainingSeconds}s remaining`);
      }
      if (event.type === "TIME_EXPIRED") {
        setTimeMessage(`${event.targetRef} · time expired`);
      }
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
      if (capabilities.vpn_filtering.level !== "FULL") {
        setProtectionMessage("Web protection permission is required.");
        return;
      }
      await GuardianProtection.startProtection();
      await api.acknowledgePolicy(policy.data.policy_version);
      const protectionStatus = await GuardianProtection.getProtectionStatus();
      const currentCapabilities = await GuardianProtection.getCapabilities();
      await api.heartbeat({
        protection_state: protectionStatus.health,
        capabilities: currentCapabilities,
      });
      setAcknowledgedVersion(policy.data.policy_version);
      setProtectionMessage("Web protection is active for DNS and known blocked destinations. Other traffic may bypass Guardian.");
      if (!usageUploaded.current) {
        usageUploaded.current = true;
        const usage = await GuardianProtection.getUsageSummary({
          start: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          end: new Date().toISOString(),
        });
        const occurredAt = new Date().toISOString();
        const events = Object.entries(usage.byTarget)
          .filter(([, seconds]) => seconds > 0)
          .map(([appRef, seconds]) => ({
            event_type: "APP_USAGE",
            occurred_at: occurredAt,
            app_ref: appRef,
            duration_seconds: Math.min(Math.round(seconds), 86400),
          }));
        if (events.length) await api.ingestEvents(events);
      }
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
              {policy.data?.version_mismatch && acknowledgedVersion !== policy.data.policy_version
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
            {appBlockedMessage ? <Text>APP_BLOCKED: {appBlockedMessage}</Text> : null}
            {timeMessage ? <Text>TIME: {timeMessage}</Text> : null}
            {protectionMessage === "Web protection permission is required." ? (
              <PrimaryButton
                label="Enable web protection"
                onPress={() => void GuardianProtection.requestVpnPermission()}
              />
            ) : null}
            <PrimaryButton label="My time" onPress={() => router.push("/child/time")} />
            <PrimaryButton label="Ask for help" onPress={() => router.push("/child/requests")} />
          </SectionSurface>
        </DataState>
      )}
    </ScreenScaffold>
  );
}
