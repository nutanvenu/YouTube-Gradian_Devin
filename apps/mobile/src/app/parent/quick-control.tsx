import { useMemo, useState } from "react";
import { Text } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { CardSurface, ListRow, ScreenScaffold, SectionSurface, TextField } from "@/design-system";

export default function ParentQuickControlRoute() {
  const router = useRouter();
  const { familyId, childId } = useLocalSearchParams<{ familyId: string; childId: string }>();
  const [search, setSearch] = useState("");
  const children = useQuery({ queryKey: ["children", familyId], queryFn: () => api.children(familyId), enabled: Boolean(familyId) });
  const child = children.data?.find((item) => item.id === childId);
  const actions = useMemo(() => [
    ["Rules", () => router.push({ pathname: "/parent/rules", params: { familyId, childId } })],
    ["Requests", () => router.push({ pathname: "/parent/requests", params: { familyId } })],
    ["Activity", () => router.push({ pathname: "/parent/activity", params: { familyId } })],
    ["Protection health", () => router.push({ pathname: "/parent/health", params: { familyId } })],
  ] as const, [childId, familyId, router]);
  const filtered = actions.filter(([label]) => label.toLowerCase().includes(search.toLowerCase()));
  return (
    <ScreenScaffold title="Quick control">
      <SectionSurface>
        <Text>{child?.name ?? "Child"} · Search a control</Text>
        <TextField label="Search" value={search} onChangeText={setSearch} />
        {filtered.length ? filtered.map(([label, onPress]) => <CardSurface key={label}><ListRow label={label} onPress={onPress} /></CardSurface>) : <Text>No matching control.</Text>}
      </SectionSurface>
    </ScreenScaffold>
  );
}
