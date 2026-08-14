import { useQuery } from "@tanstack/react-query";
import { Text } from "react-native";
import { api } from "@/api/client";
import { useNetworkStatus } from "@/state/network";
import { DataState, ScreenScaffold, SectionSurface } from "@/design-system";

export default function ChildHomeRoute() {
  const policy = useQuery({ queryKey: ["device-policy"], queryFn: () => api.policy() });
  const { isOffline } = useNetworkStatus();
  return <ScreenScaffold title="My time"><DataState state={policy.isLoading ? "loading" : isOffline ? "offline" : policy.isError ? "error" : "loaded"} onRetry={() => void policy.refetch()}><SectionSurface><Text>Policy version: {policy.data?.policy_version ?? "Unknown"}</Text><Text>{policy.data?.version_mismatch ? "Waiting for device acknowledgement." : "Policy acknowledged by this device."}</Text></SectionSurface></DataState></ScreenScaffold>;
}
