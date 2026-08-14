import { useQuery } from "@tanstack/react-query";
import { Text } from "react-native";
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
  return (
    <ScreenScaffold title="My time">
      <SectionSurface>
        <Text>Time used today</Text>
        {usage.data ? <Text>{Math.round(usage.data.totalSeconds / 60)} minutes recorded on this device.</Text> : <Text>Unknown · Usage Access is unavailable or has not reported yet.</Text>}
        <Text>Need a change? Ask a parent for more time or to unblock an app or website.</Text>
        <PrimaryButton label="Ask for help" onPress={() => router.push("/child/requests")} />
      </SectionSurface>
    </ScreenScaffold>
  );
}
