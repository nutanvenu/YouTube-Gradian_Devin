import { useState } from "react";
import { Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import * as Crypto from "expo-crypto";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Category, Routine } from "@guardian/policy-schema/types";
import { api, type Child, type PolicyMutationInput } from "@/api/client";
import { useNetworkStatus } from "@/state/network";
import { ROUTINE_CATEGORIES, ROUTINE_DAYS, routineDraft, routineFromDraft } from "@/state/routine-editor";
import { CardSurface, DataState, ListRow, PrimaryButton, SecondaryButton, ScreenScaffold, SectionSurface, TextField } from "@/design-system";

function toggle<T>(items: T[], item: T): T[] {
  return items.includes(item) ? items.filter((value) => value !== item) : [...items, item];
}

function RoutineForm({ familyId, child, routine }: { familyId: string; child: Child; routine?: Routine }) {
  const [id] = useState(() => routine?.routine_id ?? Crypto.randomUUID());
  const [draft, setDraft] = useState(() => routineDraft(routine));
  const [saved, setSaved] = useState(Boolean(routine));
  const [savedKind, setSavedKind] = useState(routine?.kind);
  const [message, setMessage] = useState<string | null>(null);
  const [pendingVersion, setPendingVersion] = useState<number | null>(null);
  const { isOffline } = useNetworkStatus();
  const queryClient = useQueryClient();
  const health = useQuery({ queryKey: ["health", familyId, child.id], queryFn: () => api.health(familyId, child.id), refetchInterval: 2000 });
  const inventory = useQuery({ queryKey: ["child-inventory", familyId, child.id], queryFn: () => api.childInventory(familyId, child.id) });
  const mutate = useMutation({
    mutationFn: (input: PolicyMutationInput) => api.mutatePolicy(familyId, child.id, input),
    onSuccess: (result, input) => {
      setSaved(true);
      if (input.operation === "ROUTINE_CREATE" || input.operation === "ROUTINE_UPDATE") {
        setSavedKind((input.value as Routine).kind);
      }
      setPendingVersion(result.policy_version);
      setMessage(`Saved policy version ${result.policy_version}.`);
      void queryClient.invalidateQueries({ queryKey: ["children", familyId] });
      void queryClient.invalidateQueries({ queryKey: ["health", familyId] });
    },
    onError: (error) => setMessage(error instanceof Error ? error.message : "Could not save this routine. Try again."),
  });
  const disabled = isOffline || mutate.isPending;
  const acknowledged = pendingVersion != null && health.data?.some((item) => item.child_profile_id === child.id && item.policy_version_applied === pendingVersion);
  const activeId = (child.policy_document as { base_policy?: { current_manual_routine_id?: string } } | undefined)?.base_policy?.current_manual_routine_id;
  const save = () => {
    try {
      const value = routineFromDraft(id, draft, routine);
      setMessage(null);
      mutate.mutate({ operation: saved ? "ROUTINE_UPDATE" : "ROUTINE_CREATE", target: id, value });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Check this routine's settings.");
    }
  };
  const blockedApps = [...new Map([
    ...(inventory.data ?? []).map((app) => [app.platform_app_id, app.display_name] as const),
    ...draft.blockedApps.map((app) => [app, (inventory.data ?? []).find((item) => item.platform_app_id === app)?.display_name ?? app] as const),
  ]).entries()];
  const categories = [...new Set([...ROUTINE_CATEGORIES, ...draft.blockedCategories])];

  return <SectionSurface>
    <Text>{routine ? `Editing ${routine.name}` : "Create a routine"}</Text>
    <TextField label="Routine name" value={draft.name} onChangeText={(name) => setDraft({ ...draft, name })} />
    <ListRow label="Routine type" value={draft.kind === "SCHEDULED" ? "Scheduled" : "Manual"} />
    <SecondaryButton label={draft.kind === "SCHEDULED" ? "Switch to manual" : "Switch to scheduled"} disabled={disabled} onPress={() => setDraft({ ...draft, kind: draft.kind === "SCHEDULED" ? "MANUAL" : "SCHEDULED" })} />
    {draft.kind === "SCHEDULED" ? <CardSurface>
      <Text>Times use your child's timezone: {child.timezone}. Overnight windows are supported; days identify the starting day.</Text>
      {ROUTINE_DAYS.map((day, index) => <SecondaryButton key={day} label={`${draft.days.includes(index + 1) ? "Remove" : "Add"} ${day}`} disabled={disabled} onPress={() => setDraft({ ...draft, days: toggle(draft.days, index + 1) })} />)}
      <TextField label="Start time (HH:MM)" value={draft.start} onChangeText={(start) => setDraft({ ...draft, start })} />
      <TextField label="End time (HH:MM)" value={draft.end} onChangeText={(end) => setDraft({ ...draft, end })} />
    </CardSurface> : <Text>Save first, then activate or deactivate this routine. Only one manual routine can be active at a time.</Text>}
    <Text>Blocked categories while this routine is active</Text>
    {categories.map((category: Category) => <SecondaryButton key={category} label={`${draft.blockedCategories.includes(category) ? "Unblock" : "Block"} ${category}`} disabled={disabled} onPress={() => setDraft({ ...draft, blockedCategories: toggle(draft.blockedCategories, category) })} />)}
    <Text>Blocked apps while this routine is active</Text>
    {inventory.isError ? <SecondaryButton label="Retry app list" onPress={() => void inventory.refetch()} /> : null}
    {blockedApps.map(([app, name]) => <SecondaryButton key={app} label={`${draft.blockedApps.includes(app) ? "Unblock" : "Block"} ${name} (${app})`} disabled={disabled} onPress={() => setDraft({ ...draft, blockedApps: toggle(draft.blockedApps, app) })} />)}
    {blockedApps.length === 0 ? <Text>Apps appear after the child device reports its inventory.</Text> : null}
    {isOffline ? <Text>You are offline. Reconnect to save or activate rules.</Text> : null}
    {message ? <Text accessibilityRole="alert">{message}</Text> : null}
    {pendingVersion != null ? <Text>{acknowledged ? "This policy version is active on the child device." : `Pending sync: waiting for the child device to acknowledge version ${pendingVersion}.`}</Text> : null}
    <PrimaryButton label={mutate.isPending ? "Saving…" : "Save routine"} disabled={disabled} onPress={save} />
    {saved && savedKind === "MANUAL" && draft.kind === "MANUAL" ? <>
      <ListRow label="Manual routine" value={activeId === id ? "Active" : "Inactive"} />
      <SecondaryButton label="Activate routine" disabled={disabled} onPress={() => mutate.mutate({ operation: "ROUTINE_ACTIVATE", target: id })} />
      <SecondaryButton label="Deactivate routine" disabled={disabled} onPress={() => mutate.mutate({ operation: "ROUTINE_DEACTIVATE", target: id })} />
    </> : null}
  </SectionSurface>;
}

export default function RoutineEditorRoute() {
  const { familyId, childId, routineId } = useLocalSearchParams<{ familyId: string; childId: string; routineId?: string }>();
  const children = useQuery({ queryKey: ["children", familyId], queryFn: () => api.children(familyId), enabled: Boolean(familyId) });
  const child = children.data?.find((item) => item.id === childId);
  const routines = (child?.policy_document as { routines?: Routine[] } | undefined)?.routines ?? [];
  const routine = routines.find((item) => item.routine_id === routineId);
  return <ScreenScaffold title="Routine editor"><DataState state={children.isLoading ? "loading" : children.isError ? "error" : "loaded"} onRetry={() => void children.refetch()}>
    {child && (!routineId || routine) ? <RoutineForm key={`${childId}:${routineId ?? "new"}`} familyId={familyId} child={child} routine={routine} /> : <Text>{routineId ? "This routine no longer exists. Return to Rules." : "Select a child from Rules before creating a routine."}</Text>}
  </DataState></ScreenScaffold>;
}
