import { useLocalSearchParams, useRouter } from "expo-router";
import { Image, Text } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useSession } from "@/auth/session";
import { useNetworkStatus } from "@/state/network";
import { CardSurface, DataState, ListRow, PrimaryButton, ResponsiveColumns, ScreenScaffold, SectionSurface, ProtectionStatePill, SecondaryButton } from "@/design-system";
import { GuardianProtection } from "../../../modules/guardian-protection/src";

export default function ParentHomeRoute() {
  const { familyId } = useLocalSearchParams<{ familyId?: string }>();
  const router = useRouter();
  const { signOut, familyId: storedFamilyId } = useSession();
  const activeFamilyId = familyId ?? storedFamilyId ?? undefined;
  const { isOffline } = useNetworkStatus();
  const children = useQuery({ queryKey: ["children", activeFamilyId], queryFn: () => api.children(activeFamilyId!), enabled: Boolean(activeFamilyId) });
  const health = useQuery({ queryKey: ["health", activeFamilyId], queryFn: () => api.health(activeFamilyId!), enabled: Boolean(activeFamilyId) });
  const capabilities = useQuery({ queryKey: ["guardian-capabilities"], queryFn: () => GuardianProtection.getCapabilities() });
  const inventory = useQuery({ queryKey: ["guardian-inventory"], queryFn: () => GuardianProtection.getObservedApps() });
  const capabilityState = capabilities.data ?? {
    app_usage: { level: "Checking" },
    accessibility_signals: { level: "Checking" },
  };
  const state = !activeFamilyId ? "empty" : children.isLoading || health.isLoading ? "loading" : isOffline ? "offline" : children.isError || health.isError ? "error" : children.data?.length ? "loaded" : "empty";
  return (
    <ScreenScaffold title="Parent home">
      {!activeFamilyId ? (
        <SectionSurface>
          <PrimaryButton label="Set up your family" onPress={() => router.push("/parent/setup")} />
        </SectionSurface>
      ) : null}
      <DataState state={state} onRetry={() => { void children.refetch(); void health.refetch(); }}>
        <ResponsiveColumns>
          {children.data?.map((child) => <CardSurface key={child.id}><Text>{child.name}</Text><ListRow label="Age band" value={child.age_band} /><PrimaryButton label="Generate pairing code" onPress={() => router.push({ pathname: "/parent/pairing", params: { familyId: activeFamilyId, childId: child.id } })} /><SecondaryButton label="Rules" onPress={() => router.push({ pathname: "/parent/rules", params: { familyId: activeFamilyId, childId: child.id } })} /><SecondaryButton label="Requests" onPress={() => router.push({ pathname: "/parent/requests", params: { familyId: activeFamilyId } })} /><SecondaryButton label="Activity" onPress={() => router.push({ pathname: "/parent/activity", params: { familyId: activeFamilyId } })} /><SecondaryButton label="Protection health" onPress={() => router.push({ pathname: "/parent/health", params: { familyId: activeFamilyId } })} /><SecondaryButton label="Quick control" onPress={() => router.push({ pathname: "/parent/quick-control", params: { familyId: activeFamilyId, childId: child.id } })} /></CardSurface>)}
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
        </ResponsiveColumns>
      </DataState>
      <PrimaryButton label="Sign out" onPress={() => { void signOut().then(() => router.replace("/role-selection")); }} />
    </ScreenScaffold>
  );
}
