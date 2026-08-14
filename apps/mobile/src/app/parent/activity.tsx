import { Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "@/api/client";
import { useNetworkStatus } from "@/state/network";
import { GuardianProtection } from "../../../modules/guardian-protection/src";
import { CardSurface, DataState, ListRow, ScreenScaffold, SectionSurface } from "@/design-system";

function startOfDay() {
  const value = new Date();
  value.setHours(0, 0, 0, 0);
  return value.toISOString();
}

function reportRange() {
  const now = new Date();
  const start = new Date(now);
  start.setDate(now.getDate() - 6);
  return {
    start: start.toISOString().slice(0, 10),
    end: new Date(now.getTime() + 86400000).toISOString().slice(0, 10),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  };
}

export default function ParentActivityRoute() {
  const { familyId } = useLocalSearchParams<{ familyId: string }>();
  const { isOffline } = useNetworkStatus();
  const activity = useQuery({ queryKey: ["activity", familyId], queryFn: () => api.activity(familyId), enabled: Boolean(familyId) });
  const activityUsage = useQuery({ queryKey: ["activity-usage", familyId], queryFn: () => api.activityUsage(familyId), enabled: Boolean(familyId) });
  const report = useQuery({
    queryKey: ["usage-report", familyId],
    queryFn: () => api.usageReport(familyId, { ...reportRange(), granularity: "DAILY" }),
    enabled: Boolean(familyId),
  });
  const usage = useQuery({
    queryKey: ["usage-summary"],
    queryFn: () => GuardianProtection.getUsageSummary({ start: startOfDay(), end: new Date().toISOString() }),
  });
  const activityEvents = activity.data ?? [];
  const activityUsagePoints = activityUsage.data ?? [];
  const reportBuckets = report.data ?? [];
  const usageTargets = usage.data?.byTarget ?? {};
  const hasData = activityEvents.length > 0 || activityUsagePoints.length > 0 || Object.keys(usageTargets).length > 0 || reportBuckets.length > 0;
  const permissionDenied =
    [activity.error, activityUsage.error, usage.error, report.error].some(
      (error) => error instanceof ApiError && error.status === 401,
    );
  const state = activity.isLoading || activityUsage.isLoading || usage.isLoading || report.isLoading
    ? "loading"
    : permissionDenied
      ? "permission-denied"
    : activity.isError || activityUsage.isError || usage.isError || report.isError
      ? "error"
      : isOffline
        ? "offline"
        : activity.isStale || activityUsage.isStale || usage.isStale
          ? "stale"
          : !activity.data || !activityUsage.data || !usage.data
        ? "loading"
            : hasData ? "loaded" : "empty";
  return (
    <ScreenScaffold title="Activity">
      <DataState state={state} onRetry={() => { void activity.refetch(); void activityUsage.refetch(); void usage.refetch(); void report.refetch(); }}>
        <SectionSurface>
          <Text>Today’s usage</Text>
          {Object.keys(usageTargets).length > 0
            ? Object.entries(usageTargets).map(([target, seconds]) => <ListRow key={target} label={target} value={`${Math.round(seconds / 60)} min`} />)
            : <Text>Unknown · this device has not provided a usage summary.</Text>}
        </SectionSurface>
        <SectionSurface>
          <Text>Daily usage report</Text>
          {reportBuckets.length
            ? reportBuckets.map((bucket) => (
              <CardSurface key={`${bucket.child_profile_id}-${bucket.period_start}`}>
                <ListRow label={bucket.period_start} value={`${Math.round(bucket.duration_seconds / 60)} min`} />
                <Text>{Object.entries(bucket.by_category).map(([category, seconds]) => `${category}: ${Math.round(seconds / 60)} min`).join(" · ")}</Text>
              </CardSurface>
            ))
            : <Text>Unknown · no persisted usage is available for this report.</Text>}
        </SectionSurface>
        <SectionSurface>
          <Text>Usage over time</Text>
          {activityUsagePoints.length ? activityUsagePoints.map((point) => (
            <CardSurface key={`${point.occurred_at}-${point.app_ref ?? "unknown"}-${point.event_type}`}>
              <ListRow label={point.app_ref ?? "Unknown app"} value={`${Math.round(point.duration_seconds / 60)} min`} />
              <Text>{point.category ?? "Unknown category"} · {new Date(point.occurred_at).toLocaleString()}</Text>
            </CardSurface>
          )) : <Text>Unknown · no usage aggregates are available for this family.</Text>}
        </SectionSurface>
        <SectionSurface>
          <Text>Web and safety events</Text>
          {activityEvents.length ? activityEvents.map((event) => (
            <CardSurface key={event.id}>
              <ListRow label={event.kind === "WEB" ? "Web event" : "Safety event"} value={event.event_type} />
              <Text>{event.domain ?? event.app_ref ?? "Unknown target"}</Text>
              <Text>{event.category ?? "Unknown category"}</Text>
              <Text>{new Date(event.occurred_at).toLocaleString()}</Text>
            </CardSurface>
          )) : <Text>Unknown · no backend events are available for this family.</Text>}
        </SectionSurface>
      </DataState>
      {state === "empty" ? (
        <SectionSurface>
          <Text>Unknown · this family has not reported activity yet.</Text>
          <Text>Unknown · no backend events are available for this family.</Text>
          <Text>Unknown · no usage aggregates are available for this family.</Text>
        </SectionSurface>
      ) : null}
    </ScreenScaffold>
  );
}
