import { useQuery } from "@tanstack/react-query";
import { Text } from "react-native";
import { api } from "@/api/client";
import { GuardianProtection } from "../../../modules/guardian-protection/src";
import { PrimaryButton, ScreenScaffold, SectionSurface } from "@/design-system";
import { useRouter } from "expo-router";

function todayRange() {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  return { start: start.toISOString(), end: new Date().toISOString() };
}

export default function ChildTimeRoute() {
  const router = useRouter();
  const usage = useQuery({ queryKey: ["child-usage"], queryFn: () => GuardianProtection.getUsageSummary(todayRange()), refetchInterval: 30_000 });
  const policy = useQuery({ queryKey: ["device-policy"], queryFn: () => api.policy() });
  const appBudgets = (() => {
    const bundle = policy.data?.bundle as { app_rules?: unknown } | undefined;
    if (!bundle || !Array.isArray(bundle.app_rules)) return [];
    const rules = bundle.app_rules as unknown[];
    return rules.filter((rule): rule is { app_ref: string; daily_minutes: number } => {
      if (typeof rule !== "object" || rule === null) return false;
      const candidate = rule as Record<string, unknown>;
      return typeof candidate.app_ref === "string" && typeof candidate.daily_minutes === "number";
    });
  })();
  return (
    <ScreenScaffold title="My time">
      <SectionSurface>
        <Text>Time used today</Text>
        {usage.data ? <Text>{Math.round(usage.data.totalSeconds / 60)} minutes recorded on this device.</Text> : <Text>Unknown · Usage Access is unavailable or has not reported yet.</Text>}
        {usage.data && appBudgets.length > 0
          ? appBudgets.map((budget) => {
              const usedSeconds = usage.data.byTarget[budget.app_ref] ?? 0;
              const remainingSeconds = Math.max(0, budget.daily_minutes * 60 - usedSeconds);
              return <Text key={budget.app_ref}>{budget.app_ref}: {Math.ceil(remainingSeconds / 60)} minutes remaining.</Text>;
            })
          : null}
        <Text>Need a change? Ask a parent for more time or to unblock an app or website.</Text>
        <PrimaryButton label="Ask for help" onPress={() => router.push("/child/requests")} />
      </SectionSurface>
    </ScreenScaffold>
  );
}
