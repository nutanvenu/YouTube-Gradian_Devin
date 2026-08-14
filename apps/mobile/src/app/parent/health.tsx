import { Alert, Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useNetworkStatus } from "@/state/network";
import { GuardianProtection } from "../../../modules/guardian-protection/src";
import { CardSurface, DataState, ListRow, PrimaryButton, ScreenScaffold, SectionSurface, ProtectionStatePill } from "@/design-system";

export default function ParentHealthRoute() {
  const { familyId } = useLocalSearchParams<{ familyId: string }>();
  const { isOffline } = useNetworkStatus();
  const health = useQuery({ queryKey: ["health", familyId], queryFn: () => api.health(familyId), enabled: Boolean(familyId), refetchInterval: 5000 });
  const capabilities = useQuery({ queryKey: ["guardian-capabilities"], queryFn: () => GuardianProtection.getCapabilities(), refetchInterval: 5000 });
  const status = useQuery({ queryKey: ["guardian-status"], queryFn: () => GuardianProtection.getProtectionStatus(), refetchInterval: 5000 });
  const explain = (title: string, message: string, onConfirm: () => void) => Alert.alert(
    title,
    `${message}\n\nGuardian does not read passwords or message content through this capability.`,
    [
      { text: "Not now", style: "cancel" },
      { text: "Open settings", onPress: onConfirm },
    ],
  );
  return (
    <ScreenScaffold title="Protection health">
      <DataState state={health.isLoading || capabilities.isLoading || status.isLoading ? "loading" : health.isError || capabilities.isError || status.isError ? "error" : isOffline ? "offline" : health.isStale || capabilities.isStale || status.isStale ? "stale" : "loaded"} onRetry={() => { void health.refetch(); void capabilities.refetch(); void status.refetch(); }}>
        <SectionSurface>
          <Text>Device health</Text>
          {health.data?.length ? health.data.map((item) => <CardSurface key={item.device_id}><ProtectionStatePill state={item.state} /><ListRow label="Last seen" value={item.last_seen_at ? new Date(item.last_seen_at).toLocaleString() : "Unknown"} /><ListRow label="Policy acknowledged" value={item.policy_version_applied === null ? "Unknown" : `Version ${item.policy_version_applied}`} /></CardSurface>) : <Text>Unknown · no paired device health is available.</Text>}
        </SectionSurface>
        <SectionSurface>
          <Text>On-device capabilities</Text>
          {Object.entries(capabilities.data ?? {}).map(([key, value]) => <CardSurface key={key}><ListRow label={key} value={value.level} /><Text>{value.detail ?? "No degraded reason reported."}</Text></CardSurface>)}
          <Text>Usage Access lets Guardian measure foreground time. Accessibility lets Guardian identify the foreground app and enforce limits. Communication safety is Android-only best effort with notification-listener consent; raw notification content is processed in memory and discarded. On iPhone/iPad: Not available on iPhone/iPad. Guardian cannot read passwords, messages, or screen content.</Text>
          <PrimaryButton label="Open Usage Access" onPress={() => explain("Usage Access", "Guardian uses Usage Access to measure foreground app time and build reports.", () => void GuardianProtection.openUsageAccessSettings())} />
          <PrimaryButton label="Open Accessibility" onPress={() => explain("Accessibility", "Guardian uses Accessibility to identify the foreground app and enforce app limits where Android allows.", () => void GuardianProtection.openAccessibilitySettings())} />
          <PrimaryButton label="Restore Communication Safety permission" onPress={() => explain("Notification access", "Guardian checks supported communication-app notifications only when Communication Safety is enabled. Raw notification text is discarded.", () => void GuardianProtection.openNotificationAccessSettings())} />
          <PrimaryButton label="Open VPN settings" onPress={() => explain("VPN web protection", "Guardian uses an Android VPN to inspect DNS destinations for policy enforcement; some traffic cannot be attributed.", () => void GuardianProtection.requestVpnPermission())} />
        </SectionSurface>
        <SectionSurface>
          <Text>Protection status</Text>
          <ListRow label="Active" value={status.data?.active === undefined ? "Unknown" : status.data.active ? "Yes" : "No"} />
          <ListRow label="Health" value={status.data?.health ?? "Unknown"} />
          <Text>{status.data?.details ?? "No degraded reason reported."}</Text>
        </SectionSurface>
      </DataState>
    </ScreenScaffold>
  );
}
