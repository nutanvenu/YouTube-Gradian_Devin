import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { Text } from "react-native";
import { ApiError, api } from "@/api/client";
import { useNetworkStatus } from "@/state/network";
import { DataState, ProtectionRemovedState, ScreenScaffold, SectionSurface } from "@/design-system";

function isRevokedDeviceError(error: unknown): boolean {
  if (error instanceof ApiError) return error.status === 401 || error.status === 403;
  if (typeof error !== "object" || error === null || !("status" in error)) return false;
  const status = error.status;
  return status === 401 || status === 403;
}

export default function ChildHomeRoute() {
  const router = useRouter();
  const policy = useQuery({ queryKey: ["device-policy"], queryFn: () => api.policy() });
  const { isOffline } = useNetworkStatus();
  const revoked = isRevokedDeviceError(policy.error);
  return (
    <ScreenScaffold title="My time">
      {revoked ? (
        <ProtectionRemovedState onRecover={() => router.replace("/role-selection")} />
      ) : (
        <DataState
          state={
            policy.isLoading
              ? "loading"
              : isOffline
                ? "offline"
                : policy.isError
                  ? "error"
                  : "loaded"
          }
          onRetry={() => void policy.refetch()}
        >
          <SectionSurface>
            <Text>Policy version: {policy.data?.policy_version ?? "Unknown"}</Text>
            <Text>
              {policy.data?.version_mismatch
                ? "Waiting for device acknowledgement."
                : "Policy acknowledged by this device."}
            </Text>
          </SectionSurface>
        </DataState>
      )}
    </ScreenScaffold>
  );
}
