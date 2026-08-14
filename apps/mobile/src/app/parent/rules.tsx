import { useMemo, useState } from "react";
import { Image, Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type PolicyMutationInput } from "@/api/client";
import { GuardianProtection } from "../../../modules/guardian-protection/src";
import {
  CardSurface,
  DataState,
  ListRow,
  PrimaryButton,
  ScreenScaffold,
  SecondaryButton,
  SectionSurface,
  TextField,
} from "@/design-system";

type PolicyRecord = Record<string, unknown>;
type AppRule = { app_ref?: string; action?: string; daily_minutes?: number };
type DomainRule = { domain?: string; action?: string };
type Routine = { routine_id: string; name: string; kind: "MANUAL" | "SCHEDULED"; blocked_categories?: string[] };

function record(value: unknown): PolicyRecord {
  return value && typeof value === "object" ? value as PolicyRecord : {};
}

function list<T>(value: unknown): T[] {
  return Array.isArray(value) ? value as T[] : [];
}

export default function ParentRulesRoute() {
  const { familyId, childId } = useLocalSearchParams<{ familyId: string; childId: string }>();
  const queryClient = useQueryClient();
  const [domain, setDomain] = useState("");
  const [minutes, setMinutes] = useState("30");
  const [message, setMessage] = useState<string | null>(null);
  const children = useQuery({
    queryKey: ["children", familyId],
    queryFn: () => api.children(familyId),
    enabled: Boolean(familyId),
  });
  const inventory = useQuery({
    queryKey: ["guardian-inventory"],
    queryFn: () => GuardianProtection.getObservedApps(),
  });
  const health = useQuery({
    queryKey: ["health", familyId],
    queryFn: () => api.health(familyId),
    enabled: Boolean(familyId),
    refetchInterval: 2000,
  });
  const [pendingVersion, setPendingVersion] = useState<number | null>(null);
  const mutate = useMutation({
    mutationFn: (input: PolicyMutationInput) => api.mutatePolicy(familyId, childId, input),
    onSuccess: (result) => {
      setPendingVersion(result.policy_version);
      setMessage(`Saved policy version ${result.policy_version}. Waiting for device acknowledgement.`);
      void queryClient.invalidateQueries({ queryKey: ["children", familyId] });
      void queryClient.invalidateQueries({ queryKey: ["health", familyId] });
    },
    onError: (error) => setMessage(error instanceof Error ? error.message : "This rule could not be saved."),
  });
  const child = children.data?.find((item) => item.id === childId);
  const policy = record(child?.policy_document);
  const appRules = list<AppRule>(policy.app_rules);
  const domainRules = list<DomainRule>(policy.domain_rules);
  const basePolicy = record(policy.base_policy);
  const routines = list<Routine>(policy.routines);
  const acknowledged = health.data?.some((item) => item.child_profile_id === childId && item.policy_version_applied === pendingVersion);
  const syncState = pendingVersion === null || acknowledged ? "Rules active on device." : `Pending sync · device has not acknowledged version ${pendingVersion}.`;
  const apps = useMemo(() => inventory.data ?? [], [inventory.data]);

  const save = (input: PolicyMutationInput) => {
    setMessage(null);
    mutate.mutate(input);
  };

  return (
    <ScreenScaffold title="Rules">
      <DataState state={children.isLoading || inventory.isLoading ? "loading" : children.isError || inventory.isError ? "error" : "loaded"} onRetry={() => { void children.refetch(); void inventory.refetch(); }}>
        <SectionSurface>
          <Text>{child?.name ?? "Child"} · {syncState}</Text>
          <Text>Changes are not active until this device acknowledges the new policy version.</Text>
          {message ? <Text accessibilityLiveRegion="polite">{message}</Text> : null}
        </SectionSurface>
        <SectionSurface>
          <Text>App controls</Text>
          {apps.map((app) => {
            const rule = appRules.find((candidate) => candidate.app_ref === app.platformAppId);
            return (
              <CardSurface key={app.platformAppId}>
                {app.iconUri ? <Image source={{ uri: app.iconUri }} accessibilityLabel={`${app.displayName} icon`} style={{ width: 36, height: 36 }} /> : null}
                <ListRow label={app.displayName} value={`${rule?.action ?? "No rule"}${app.newlyObserved ? " · New app" : ""}`} />
                <SecondaryButton label="Allow" onPress={() => save({ operation: "APP_ALLOW", target: app.platformAppId })} />
                <SecondaryButton label="Block" onPress={() => save({ operation: "APP_BLOCK", target: app.platformAppId })} />
                <SecondaryButton label={`Limit to ${minutes || "30"} minutes`} onPress={() => save({ operation: "APP_DAILY_MINUTES", target: app.platformAppId, value: Number(minutes) || 30 })} />
                <SecondaryButton label="Unlimited" onPress={() => save({ operation: "APP_UNLIMITED", target: app.platformAppId })} />
              </CardSurface>
            );
          })}
          <TextField label="Daily limit minutes" value={minutes} onChangeText={setMinutes} keyboardType="numeric" />
        </SectionSurface>
        <SectionSurface>
          <Text>Website controls</Text>
          {domainRules.map((rule) => <ListRow key={`${rule.domain}-${rule.action}`} label={rule.domain ?? "Unknown domain"} value={rule.action ?? "Unknown"} />)}
          <TextField label="Website or domain" value={domain} onChangeText={setDomain} keyboardType="default" />
          <PrimaryButton label="Block website" disabled={!domain.trim()} onPress={() => save({ operation: "DOMAIN_BLOCK", target: domain.trim() })} />
          <SecondaryButton label="Allow website" disabled={!domain.trim()} onPress={() => save({ operation: "DOMAIN_ALLOW", target: domain.trim() })} />
          <Text>Unknown websites: {typeof basePolicy.unknown_domain_policy === "string" ? basePolicy.unknown_domain_policy : "Unknown"}</Text>
          <SecondaryButton label="Block unknown websites" onPress={() => save({ operation: "UNKNOWN_DOMAIN_POLICY", target: "unknown", value: "BLOCK" })} />
          <SecondaryButton label="Allow unknown websites with notice" onPress={() => save({ operation: "UNKNOWN_DOMAIN_POLICY", target: "unknown", value: "ALLOW_AND_NOTIFY" })} />
        </SectionSurface>
        <SectionSurface>
          <Text>Category budgets</Text>
          {["SOCIAL_MEDIA", "STREAMING_VIDEO", "GAMES", "MESSAGING"].map((category) => (
            <CardSurface key={category}>
              <ListRow label={category} value="Set a daily budget from the app limit field." />
              <SecondaryButton label={`Limit ${category}`} onPress={() => save({ operation: "CATEGORY_DAILY_MINUTES", target: category, value: Number(minutes) || 30 })} />
            </CardSurface>
          ))}
          <Text>Web strictness is applied through category rules and unknown-content policy.</Text>
          <SecondaryButton label="Block social media" onPress={() => save({ operation: "WEB_CATEGORY_BLOCK", target: "SOCIAL_MEDIA" })} />
        </SectionSurface>
        <SectionSurface>
          <Text>Routines</Text>
          {routines.map((routine) => (
            <CardSurface key={routine.routine_id}>
              <ListRow label={routine.name} value={routine.kind} />
              <SecondaryButton label="Delete routine" onPress={() => save({ operation: "ROUTINE_DELETE", target: routine.routine_id })} />
            </CardSurface>
          ))}
          <PrimaryButton
            label="Add manual routine"
            onPress={() => save({
              operation: "ROUTINE_CREATE",
              target: "new",
              value: { routine_id: `manual-${Date.now()}`, name: "Focus time", kind: "MANUAL", blocked_categories: ["SOCIAL_MEDIA", "GAMES"] },
            })}
          />
          <Text>Manual activation is shown only when the child device exposes a local routine activation control.</Text>
        </SectionSurface>
      </DataState>
    </ScreenScaffold>
  );
}
