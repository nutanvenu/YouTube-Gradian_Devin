import { useLocalSearchParams, useRouter } from "expo-router";
import { Text } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useSession } from "@/auth/session";
import { useNetworkStatus } from "@/state/network";
import { CardSurface, DataState, ListRow, PrimaryButton, ScreenScaffold, SectionSurface, ProtectionStatePill } from "@/design-system";

export default function ParentHomeRoute() {
  const { familyId } = useLocalSearchParams<{ familyId?: string }>();
  const router = useRouter();
  const { signOut } = useSession();
  const { isOffline } = useNetworkStatus();
  const children = useQuery({ queryKey: ["children", familyId], queryFn: () => api.children(familyId!), enabled: Boolean(familyId) });
  const health = useQuery({ queryKey: ["health", familyId], queryFn: () => api.health(familyId!), enabled: Boolean(familyId) });
  const state = !familyId ? "empty" : children.isLoading || health.isLoading ? "loading" : isOffline ? "offline" : children.isError || health.isError ? "error" : children.data?.length ? "loaded" : "empty";
  return (
    <ScreenScaffold title="Parent home">
      <DataState state={state} onRetry={() => { void children.refetch(); void health.refetch(); }}>
        <SectionSurface>
          {children.data?.map((child) => <CardSurface key={child.id}><Text>{child.name}</Text><ListRow label="Age band" value={child.age_band} /><PrimaryButton label="Generate pairing code" onPress={() => router.push({ pathname: "/parent/pairing", params: { familyId, childId: child.id } })} /></CardSurface>)}
          {health.data?.map((item) => <CardSurface key={item.device_id}><ListRow label="Protection" value={item.last_seen_at ?? "Unknown"} /><ProtectionStatePill state={item.state} /></CardSurface>)}
        </SectionSurface>
      </DataState>
      <PrimaryButton label="Sign out" onPress={() => { void signOut().then(() => router.replace("/role-selection")); }} />
    </ScreenScaffold>
  );
}
