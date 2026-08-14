import { useLocalSearchParams, useRouter } from "expo-router";
import { Image, Text } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useSession } from "@/auth/session";
import { useNetworkStatus } from "@/state/network";
import { CardSurface, DataState, ListRow, PrimaryButton, ScreenScaffold, SectionSurface, ProtectionStatePill } from "@/design-system";
import { GuardianProtection } from "../../../modules/guardian-protection/src";

export default function ParentHomeRoute() {
  const { familyId } = useLocalSearchParams<{ familyId?: string }>();
  const router = useRouter();
  const { signOut } = useSession();
  const { isOffline } = useNetworkStatus();
  const children = useQuery({ queryKey: ["children", familyId], queryFn: () => api.children(familyId!), enabled: Boolean(familyId) });
  const health = useQuery({ queryKey: ["health", familyId], queryFn: () => api.health(familyId!), enabled: Boolean(familyId) });
  const capabilities = useQuery({ queryKey: ["guardian-capabilities"], queryFn: () => GuardianProtection.getCapabilities() });
  const inventory = useQuery({ queryKey: ["guardian-inventory"], queryFn: () => GuardianProtection.getObservedApps() });
  const capabilityState = capabilities.data ?? {
    app_usage: { level: "Checking" },
    accessibility_signals: { level: "Checking" },
  };
  const state = !familyId ? "empty" : children.isLoading || health.isLoading ? "loading" : isOffline ? "offline" : children.isError || health.isError ? "error" : children.data?.length ? "loaded" : "empty";
  return (
    <ScreenScaffold title="Parent home">
      <DataState state={state} onRetry={() => { void children.refetch(); void health.refetch(); }}>
        <SectionSurface>
          {children.data?.map((child) => <CardSurface key={child.id}><Text>{child.name}</Text><ListRow label="Age band" value={child.age_band} /><PrimaryButton label="Generate pairing code" onPress={() => router.push({ pathname: "/parent/pairing", params: { familyId, childId: child.id } })} /></CardSurface>)}
          {health.data?.map((item) => <CardSurface key={item.device_id}><ListRow label="Protection" value={item.last_seen_at ?? "Unknown"} /><ProtectionStatePill state={item.state} /></CardSurface>)}
          <CardSurface>
            <Text>Protection permissions</Text>
            <Text>Usage Access lets Guardian measure foreground time. Accessibility lets Guardian identify the foreground app and enforce limits. Guardian cannot read passwords, messages, or screen content.</Text>
            <ListRow label="Usage Access" value={capabilityState.app_usage.level} onPress={() => void GuardianProtection.openUsageAccessSettings()} />
            <ListRow label="Accessibility" value={capabilityState.accessibility_signals.level} onPress={() => void GuardianProtection.openAccessibilitySettings()} />
            <ListRow
              label="Web protection"
              value={capabilities.data?.web_filtering.level ?? "Checking"}
            />
            <Text>
              Guardian protects DNS requests and destinations identified as blocked by policy.
              Unrouted traffic, some QUIC/DoH flows, and IP-only traffic may bypass domain attribution.
            </Text>
          </CardSurface>
          <CardSurface>
            <Text>Installed apps</Text>
            {inventory.data?.map((app) => (
              <ListRow
                key={app.platformAppId}
                label={app.displayName}
                value={`${app.category}${app.newlyObserved ? " · New" : ""}`}
              />
            ))}
            {inventory.data?.filter((app) => app.iconUri).map((app) => (
              <Image
                key={`${app.platformAppId}-icon`}
                source={{ uri: app.iconUri! }}
                accessibilityLabel={`${app.displayName} icon`}
                style={{ width: 32, height: 32 }}
              />
            ))}
          </CardSurface>
        </SectionSurface>
      </DataState>
      <PrimaryButton label="Sign out" onPress={() => { void signOut().then(() => router.replace("/role-selection")); }} />
    </ScreenScaffold>
  );
}
