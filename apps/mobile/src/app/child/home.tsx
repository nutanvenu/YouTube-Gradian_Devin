import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { Alert, AppState, Platform, Text } from "react-native";
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
  const inventoryUploaded = useRef(false);

  const syncReputation = async () => {
    const status = await GuardianProtection.getReputationStatus();
    const response = await api.reputation(status.version ?? 0);
    const bundles = response.bundle ? [response.bundle, ...response.deltas] : response.deltas;
    for (const bundle of bundles) {
      const result = await GuardianProtection.applyReputationBundle(bundle);
      if (!result.applied && result.reason === "DELTA_GAP") {
        const full = await api.reputation(0);
        if (full.bundle) {
          const fallback = await GuardianProtection.applyReputationBundle(full.bundle);
          if (!fallback.applied) throw new Error(`Reputation full bundle rejected: ${fallback.reason}`);
        }
        break;
      }
      if (!result.applied && result.reason !== "VERSION_NOT_MONOTONIC") {
        throw new Error(`Reputation bundle rejected: ${result.reason}`);
      }
    }
  };

  useEffect(() => {
    let mounted = true;
    void sessionStorage.getFamilyId().then((value) => {
      if (mounted) setFamilyId(value ?? undefined);
    });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (__DEV__ && Platform.OS === "android") {
      void GuardianProtection.getPerformanceMetrics()
        .then((metrics) => {
          console.info("GUARDIAN_PERFORMANCE_METRICS", JSON.stringify(metrics));
        })
        .catch(() => {
          console.info("GUARDIAN_PERFORMANCE_METRICS_UNAVAILABLE");
        });
    }
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
        }], event.correlationId).catch(() => undefined);
        if (event.domain && event.reasonCode.startsWith("REPUTATION_PENDING")) {
          void api.classifyDomain(event.domain)
            .then(() => syncReputation())
            .catch(() => undefined);
        }
      }
      if (event.type === "SAFETY_EVENT") {
        void api.ingestEvents([{
          event_type: `SAFETY_${event.category}`,
          occurred_at: event.occurredAt,
          app_ref: event.appRef ?? null,
          category: event.category,
          severity: event.severity,
          confidence: event.confidence,
          reason_code: event.reasonCode,
        }], event.correlationId).catch(() => undefined);
      }
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
      const communication = policy.data.bundle as { communication_safety?: { enabled?: boolean } };
      if (communication.communication_safety?.enabled && capabilities.communication_risk_signals.level === "UNAVAILABLE") {
        setProtectionMessage("Communication safety permission is required.");
      }
      await GuardianProtection.startProtection();
      await syncReputation();
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
      if (!inventoryUploaded.current) {
        const observedApps = await GuardianProtection.getObservedApps();
        await api.ingestInventory(
          observedApps.map((app) => ({
            platform_app_id: app.platformAppId,
            display_name: app.displayName,
            category: app.category,
            observed_at: app.observedAt,
          })),
        );
        inventoryUploaded.current = true;
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
            <Text>
              Communication Safety checks notification signals from supported communication apps.
              Guardian analyzes notification text briefly on this device, discards it, and sends
              only category, severity, confidence, source app, time, and reason. Guardian cannot
              read message history, passwords, or content outside notifications.
            </Text>
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
                onPress={() => Alert.alert(
                  "VPN web protection",
                  "Guardian uses an Android VPN to inspect DNS destinations for policy enforcement. It does not provide full-device traffic visibility. Unrouted traffic, some QUIC/DoH flows, and IP-only traffic may bypass domain attribution.",
                  [
                    { text: "Not now", style: "cancel" },
                    { text: "Allow VPN", onPress: () => void GuardianProtection.requestVpnPermission() },
                  ],
                )}
              />
            ) : null}
            {protectionMessage === "Communication safety permission is required." ? (
              <PrimaryButton
                label="Restore communication safety permission"
                onPress={() => Alert.alert(
                  "Notification access",
                  "With Communication Safety enabled, Guardian checks only supported communication-app notifications. Raw notification text is processed briefly on this device and discarded; only category, severity, source app, time, confidence, and reason metadata leave the device.",
                  [
                    { text: "Not now", style: "cancel" },
                    { text: "Open notification settings", onPress: () => void GuardianProtection.openNotificationAccessSettings() },
                  ],
                )}
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
