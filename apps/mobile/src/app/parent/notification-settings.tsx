import { Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { CardSurface, DataState, ListRow, ScreenScaffold, SectionSurface } from "@/design-system";

export default function NotificationSettingsRoute() {
  const { familyId } = useLocalSearchParams<{ familyId: string }>();
  const health = useQuery({ queryKey: ["health", familyId], queryFn: () => api.health(familyId), enabled: Boolean(familyId) });
  return <ScreenScaffold title="Notification settings"><DataState state={health.isLoading ? "loading" : health.isError ? "error" : "loaded"} onRetry={() => void health.refetch()}><SectionSurface><CardSurface><ListRow label="Push delivery" value="Backend action payloads enabled" /><Text>Notifications contain category, severity, source app and time. Guardian never uploads message content.</Text></CardSurface></SectionSurface><SectionSurface><Text>Current device delivery state</Text>{(health.data ?? []).map((item) => <ListRow key={item.device_id} label={item.device_id} value={item.state} />)}</SectionSurface></DataState></ScreenScaffold>;
}
