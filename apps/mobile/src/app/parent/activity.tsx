import { Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useNetworkStatus } from "@/state/network";
import { GuardianProtection } from "../../../modules/guardian-protection/src";
import { CardSurface, DataState, ListRow, ScreenScaffold, SectionSurface } from "@/design-system";

function startOfDay() {
  const value = new Date();
  value.setHours(0, 0, 0, 0);
  return value.toISOString();
}

export default function ParentActivityRoute() {
  const { familyId } = useLocalSearchParams<{ familyId: string }>();
  const { isOffline } = useNetworkStatus();
  const activity = useQuery({ queryKey: ["activity", familyId], queryFn: () => api.activity(familyId), enabled: Boolean(familyId) });
  const activityUsage = useQuery({ queryKey: ["activity-usage", familyId], queryFn: () => api.activityUsage(familyId), enabled: Boolean(familyId) });
  const usage = useQuery({
    queryKey: ["usage-summary"],
    queryFn: () => GuardianProtection.getUsageSummary({ start: startOfDay(), end: new Date().toISOString() }),
  });
  return (
    <ScreenScaffold title="Activity">
      <DataState state={activity.isLoading || activityUsage.isLoading || usage.isLoading ? "loading" : activity.isError || activityUsage.isError || usage.isError ? "error" : isOffline ? "offline" : activity.isStale || activityUsage.isStale || usage.isStale ? "stale" : "loaded"} onRetry={() => { void activity.refetch(); void activityUsage.refetch(); void usage.refetch(); }}>
        <SectionSurface>
          <Text>Today’s usage</Text>
          {usage.data?.byTarget && Object.keys(usage.data.byTarget).length > 0
            ? Object.entries(usage.data.byTarget).map(([target, seconds]) => <ListRow key={target} label={target} value={`${Math.round(seconds / 60)} min`} />)
            : <Text>Unknown · this device has not provided a usage summary.</Text>}
        </SectionSurface>
        <SectionSurface>
          <Text>Usage over time</Text>
          {activityUsage.data?.length ? activityUsage.data.map((point) => (
            <CardSurface key={`${point.occurred_at}-${point.app_ref ?? "unknown"}-${point.event_type}`}>
              <ListRow label={point.app_ref ?? "Unknown app"} value={`${Math.round(point.duration_seconds / 60)} min`} />
              <Text>{point.category ?? "Unknown category"} · {new Date(point.occurred_at).toLocaleString()}</Text>
            </CardSurface>
          )) : <Text>Unknown · no usage aggregates are available for this family.</Text>}
        </SectionSurface>
        <SectionSurface>
          <Text>Web and safety events</Text>
          {activity.data?.length ? activity.data.map((event) => (
            <CardSurface key={event.id}>
              <ListRow label={event.kind === "WEB" ? "Web event" : "Safety event"} value={event.event_type} />
              <Text>{event.domain ?? event.app_ref ?? "Unknown target"}</Text>
              <Text>{event.category ?? "Unknown category"}</Text>
              <Text>{new Date(event.occurred_at).toLocaleString()}</Text>
            </CardSurface>
          )) : <Text>Unknown · no backend events are available for this family.</Text>}
        </SectionSurface>
      </DataState>
    </ScreenScaffold>
  );
}
