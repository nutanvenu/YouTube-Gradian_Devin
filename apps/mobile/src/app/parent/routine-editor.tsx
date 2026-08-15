import { Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { CardSurface, DataState, ListRow, PrimaryButton, ScreenScaffold, SectionSurface } from "@/design-system";

function displayValue(value: unknown, fallback = "Unknown") {
  if (value === undefined || value === null) return fallback;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

export default function RoutineEditorRoute() {
  const { familyId, childId, routineId } = useLocalSearchParams<{ familyId: string; childId: string; routineId?: string }>();
  const queryClient = useQueryClient();
  const children = useQuery({ queryKey: ["children", familyId], queryFn: () => api.children(familyId), enabled: Boolean(familyId) });
  const child = children.data?.find((item) => item.id === childId);
  const routines = (child?.policy_document as { routines?: Array<Record<string, unknown>> } | undefined)?.routines ?? [];
  const routine = routines.find((item) => item.routine_id === routineId);
  const save = useMutation({ mutationFn: (operation: "ROUTINE_ACTIVATE" | "ROUTINE_DEACTIVATE") => api.mutatePolicy(familyId, childId, { operation, target: String(routineId) }), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["children", familyId] }) });
  return <ScreenScaffold title="Routine editor"><DataState state={children.isLoading ? "loading" : children.isError ? "error" : "loaded"} onRetry={() => void children.refetch()}><SectionSurface>{routine ? <CardSurface><ListRow label="Name" value={displayValue(routine.name ?? routine.routine_id)} /><ListRow label="Kind" value={displayValue(routine.kind)} /><Text>{JSON.stringify(routine)}</Text><PrimaryButton label="Activate routine" onPress={() => save.mutate("ROUTINE_ACTIVATE")} /><PrimaryButton label="Deactivate routine" onPress={() => save.mutate("ROUTINE_DEACTIVATE")} /></CardSurface> : <Text>No routine selected. Choose a routine from Rules.</Text>}</SectionSurface></DataState></ScreenScaffold>;
}
