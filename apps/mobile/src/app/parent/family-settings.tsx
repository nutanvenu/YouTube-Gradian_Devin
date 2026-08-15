import { Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { CardSurface, DataState, ListRow, ScreenScaffold, SectionSurface } from "@/design-system";

export default function FamilySettingsRoute() {
  const { familyId } = useLocalSearchParams<{ familyId: string }>();
  const family = useQuery({ queryKey: ["family", familyId], queryFn: () => api.family(familyId), enabled: Boolean(familyId) });
  const children = useQuery({ queryKey: ["children", familyId], queryFn: () => api.children(familyId), enabled: Boolean(familyId) });
  return <ScreenScaffold title="Family settings"><DataState state={family.isLoading || children.isLoading ? "loading" : family.isError || children.isError ? "error" : "loaded"} onRetry={() => { void family.refetch(); void children.refetch(); }}><SectionSurface>{family.data ? <CardSurface><ListRow label="Family" value={family.data.name} /><Text>Family membership and child profiles are managed by the Guardian family service.</Text></CardSurface> : <Text>No family is selected.</Text>}</SectionSurface><SectionSurface><Text>Children</Text>{(children.data ?? []).map((child) => <ListRow key={child.id} label={child.name} value={child.age_band} />)}</SectionSurface></DataState></ScreenScaffold>;
}
