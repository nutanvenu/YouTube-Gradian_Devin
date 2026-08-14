import { useRouter } from "expo-router";
import { Alert, Text } from "react-native";
import { PrimaryButton, ScreenScaffold, SecondaryButton, SectionSurface } from "@/design-system";
import { roleStorage } from "@/state/role";

export default function RoleSelectionRoute() {
  const router = useRouter();
  const choose = async (role: "parent" | "child") => {
    await roleStorage.set(role);
    router.replace(role === "parent" ? "/parent/login" : "/child/pair");
  };
  return (
    <ScreenScaffold title="Welcome to Guardian">
      <SectionSurface>
        <Text accessibilityRole="header">Choose how this device will be used.</Text>
        <PrimaryButton label="Parent device" onPress={() => choose("parent")} />
        <SecondaryButton label="Child device" onPress={() => Alert.alert("Parent authentication required", "A child device can only leave this mode after a parent authenticates.")} />
      </SectionSurface>
    </ScreenScaffold>
  );
}
