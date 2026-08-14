import { useState } from "react";
import { useRouter } from "expo-router";
import { Text } from "react-native";
import { ApiError, api } from "@/api/client";
import { useSession } from "@/auth/session";
import { PrimaryButton, ScreenScaffold, SectionSurface, TextField } from "@/design-system";

export default function ParentSetupRoute() {
  const router = useRouter();
  const { setFamilyId } = useSession();
  const [family, setFamily] = useState("");
  const [child, setChild] = useState("");
  const [dob, setDob] = useState("");
  const [timezone, setTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone);
  const [message, setMessage] = useState<string | null>(null);
  const submit = async () => {
    try {
      const createdFamily = await api.createFamily(family);
      const createdChild = await api.createChild(createdFamily.id, { name: child, date_of_birth: dob, timezone });
      await setFamilyId(createdFamily.id);
      setMessage(`Age band: ${createdChild.age_band}`);
      router.replace({ pathname: "/parent/home", params: { familyId: createdFamily.id } });
    } catch (error) { setMessage(error instanceof ApiError ? error.message : "Setup failed."); }
  };
  return (
    <ScreenScaffold title="Set up your family">
      <SectionSurface>
        <TextField label="Family name" value={family} onChangeText={setFamily} />
        <TextField label="Child name" value={child} onChangeText={setChild} />
        <TextField label="Date of birth (YYYY-MM-DD)" value={dob} onChangeText={setDob} />
        <TextField label="Timezone" value={timezone} onChangeText={setTimezone} />
        {message ? <Text accessibilityLiveRegion="polite">{message}</Text> : null}
        <PrimaryButton label="Create family and child" onPress={submit} disabled={!family || !child || !dob || !timezone} />
      </SectionSurface>
    </ScreenScaffold>
  );
}
