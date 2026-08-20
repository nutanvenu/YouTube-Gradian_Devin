import { useLocalSearchParams, useRouter } from "expo-router";
import { Alert, Image, Text } from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, sessionStorage } from "@/api/client";
import { useSession } from "@/auth/session";
import { useNetworkStatus } from "@/state/network";
import { CardSurface, DataState, ListRow, PrimaryButton, ResponsiveColumns, ScreenScaffold, SectionSurface, ProtectionStatePill, SecondaryButton } from "@/design-system";
import { GuardianProtection } from "../../../modules/guardian-protection/src";

export default function ParentHomeRoute() {
  const { familyId } = useLocalSearchParams<{ familyId?: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { signOut, familyId: storedFamilyId, sessionError } = useSession();
  const activeFamilyId = familyId ?? storedFamilyId ?? undefined;
  const { isOffline } = useNetworkStatus();
  const children = useQuery({ queryKey: ["children", activeFamilyId], queryFn: () => api.children(activeFamilyId!), enabled: Boolean(activeFamilyId) });
  const health = useQuery({ queryKey: ["health", activeFamilyId], queryFn: () => api.health(activeFamilyId!), enabled: Boolean(activeFamilyId) });
  const capabilities = useQuery({ queryKey: ["guardian-capabilities"], queryFn: () => GuardianProtection.getCapabilities() });
  const inventory = useQuery({ queryKey: ["guardian-inventory"], queryFn: () => GuardianProtection.getObservedApps() });
  const policyMutation = useMutation({
    mutationFn: ({ childId, operation }: { childId: string; operation: "TEMPORARY_SCREEN_TIME" | "PAUSE_INTERNET" }) =>
      api.mutatePolicy(activeFamilyId!, childId, {
        operation,
        target: operation === "PAUSE_INTERNET" ? "pause-internet" : "device",
        ...(operation === "TEMPORARY_SCREEN_TIME" ? { value: 15, expires_at: new Date(Date.now() + 15 * 60_000).toISOString() } : {}),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["children", activeFamilyId] });
      void queryClient.invalidateQueries({ queryKey: ["health", activeFamilyId] });
    },
  });
  const capabilityState = capabilities.data ?? {
    app_usage: { level: "Checking" },
    accessibility_signals: { level: "Checking" },
  };
  const explainCapability = (capability: string, explanation: string, open: () => void) => {
    Alert.alert(
      `${capability} access`,
      `${explanation}\n\nGuardian never reads editable input or password fields. When an enabled safety capability exposes notification or active-window text, Guardian processes it briefly on-device and immediately discards the raw text.`,
      [
        { text: "Not now", style: "cancel" },
        { text: `Open ${capability} settings`, onPress: open },
      ],
    );
  };
  const deleteAccount = () => {
    Alert.alert(
      "Delete account and family data?",
      "This permanently deletes your account, family, child profiles, devices, policies, events, reports, requests, and notification records. This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete permanently",
          style: "destructive",
          onPress: () => {
            void api.deleteAccount()
              .then(() => sessionStorage.clear())
              .then(() => signOut())
              .then(() => router.replace("/role-selection"));
          },
        },
      ],
    );
  };
  const state = !activeFamilyId ? "empty" : children.isLoading || health.isLoading ? "loading" : isOffline ? "offline" : children.isError || health.isError ? "error" : children.data?.length ? "loaded" : "empty";
  return (
    <ScreenScaffold title="Parent home">
      {sessionError === "SESSION_EXPIRED" ? (
        <SectionSurface>
          <Text accessibilityRole="alert">Your parent session expired. Sign in again to change Guardian rules.</Text>
          <PrimaryButton label="Sign in again" onPress={() => router.replace("/parent/login")} />
        </SectionSurface>
      ) : null}
      {!activeFamilyId ? (
        <SectionSurface>
          <PrimaryButton label="Set up your family" onPress={() => router.push("/parent/setup")} />
        </SectionSurface>
      ) : null}
      <DataState state={state} onRetry={() => { void children.refetch(); void health.refetch(); }}>
        <ResponsiveColumns>
          {children.data?.map((child) => <CardSurface key={child.id}><Text>{child.name}</Text><ListRow label="Age band" value={child.age_band} /><PrimaryButton label="Add 15 minutes" onPress={() => policyMutation.mutate({ childId: child.id, operation: "TEMPORARY_SCREEN_TIME" })} /><PrimaryButton label="Pause child internet" onPress={() => policyMutation.mutate({ childId: child.id, operation: "PAUSE_INTERNET" })} /><SecondaryButton label="Child detail" onPress={() => router.push({ pathname: "/parent/child-detail", params: { familyId: activeFamilyId, childId: child.id } })} /><PrimaryButton label="Generate pairing code" onPress={() => router.push({ pathname: "/parent/pairing", params: { familyId: activeFamilyId, childId: child.id } })} /><SecondaryButton label="Rules" onPress={() => router.push({ pathname: "/parent/rules", params: { familyId: activeFamilyId, childId: child.id } })} /><SecondaryButton label="Requests" onPress={() => router.push({ pathname: "/parent/requests", params: { familyId: activeFamilyId } })} /><SecondaryButton label="Activity" onPress={() => router.push({ pathname: "/parent/activity", params: { familyId: activeFamilyId } })} /><SecondaryButton label="Protection health" onPress={() => router.push({ pathname: "/parent/health", params: { familyId: activeFamilyId } })} /><SecondaryButton label="Quick control" onPress={() => router.push({ pathname: "/parent/quick-control", params: { familyId: activeFamilyId, childId: child.id } })} /></CardSurface>)}
          {health.data?.map((item) => <CardSurface key={item.device_id}><ListRow label="Protection" value={item.last_seen_at ?? "Unknown"} /><ProtectionStatePill state={item.state} /></CardSurface>)}
          <CardSurface>
            <Text>Protection permissions</Text>
            <Text>
              Guardian asks for each sensitive Android capability only after you choose to enable
              it. VPN filters DNS destinations; Usage Access measures foreground app time;
              Accessibility identifies the foreground app and supports app limits; notification
              access checks supported communication notifications for opt-in safety signals.
              Notification text is processed briefly on-device and discarded.
            </Text>
            <ListRow
              label="Usage Access"
              value={capabilityState.app_usage.level}
              onPress={() => explainCapability(
                "Usage Access",
                "Guardian uses this to measure foreground app time and build screen-time reports.",
                () => void GuardianProtection.openUsageAccessSettings(),
              )}
            />
            <ListRow
              label="Accessibility"
              value={capabilityState.accessibility_signals.level}
              onPress={() => explainCapability(
                "Accessibility",
                "Guardian uses this to identify the foreground app and enforce app limits where Android allows.",
                () => void GuardianProtection.openAccessibilitySettings(),
              )}
            />
            <ListRow
              label="Web protection"
              value={capabilities.data?.web_filtering.level ?? "Checking"}
              onPress={() => explainCapability(
                "VPN",
                "Guardian uses an Android VPN to inspect DNS destinations for policy enforcement. It does not provide full-device traffic visibility.",
                () => void GuardianProtection.requestVpnPermission(),
              )}
            />
            <ListRow
              label="Notification access"
              value={capabilities.data?.communication_risk_signals.level ?? "Checking"}
              onPress={() => explainCapability(
                "Notification access",
                "Guardian checks only supported communication-app notifications when Communication Safety is enabled. Raw notification text is discarded and only minimized category, severity, app, time, confidence, and reason metadata is sent.",
                () => void GuardianProtection.openNotificationAccessSettings(),
              )}
            />
            <Text>
              Guardian protects DNS requests and destinations identified as blocked by policy.
              Unrouted traffic, some QUIC/DoH flows, and IP-only traffic may bypass domain attribution.
            </Text>
          </CardSurface>
          <CardSurface>
            <Text>Installed apps</Text>
            {inventory.data?.map((app) => (
              <ListRow
                key={app.platformAppId}
                label={app.displayName}
                value={`${app.category}${app.newlyObserved ? " · New" : ""}`}
              />
            ))}
            {inventory.data?.filter((app) => app.iconUri).map((app) => (
              <Image
                key={`${app.platformAppId}-icon`}
                source={{ uri: app.iconUri! }}
                accessibilityLabel={`${app.displayName} icon`}
                style={{ width: 32, height: 32 }}
              />
            ))}
          </CardSurface>
        </ResponsiveColumns>
      </DataState>
      <SectionSurface>
        <SecondaryButton label="Family settings" onPress={() => router.push({ pathname: "/parent/family-settings", params: { familyId: activeFamilyId } })} />
        <SecondaryButton label="Guardian and device settings" onPress={() => router.push({ pathname: "/parent/guardian-device-settings", params: { familyId: activeFamilyId } })} />
        <Text>Account and data</Text>
        <Text>
          You can permanently delete your Guardian account and all family and child data from
          this device. Deletion is irreversible.
        </Text>
        <SecondaryButton label="Delete account and family data" onPress={deleteAccount} />
      </SectionSurface>
      <PrimaryButton label="Sign out" onPress={() => { void signOut().then(() => router.replace("/role-selection")); }} />
    </ScreenScaffold>
  );
}
