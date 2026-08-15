import { Text } from "react-native";
import { useRouter } from "expo-router";
import { PrimaryButton, ScreenScaffold, SectionSurface } from "@/design-system";

export default function ChildTimeUpRoute() {
  const router = useRouter();
  return <ScreenScaffold title="Time is up"><SectionSurface><Text>This time limit has ended. You can ask a parent for more time, but access stays blocked until approval reaches this device.</Text><PrimaryButton label="Ask for more time" onPress={() => router.push("/child/requests")} /><PrimaryButton label="View my time" onPress={() => router.push("/child/time")} /></SectionSurface></ScreenScaffold>;
}
