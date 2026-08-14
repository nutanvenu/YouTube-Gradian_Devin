import { useState } from "react";
import { Link, useRouter } from "expo-router";
import { Text } from "react-native";
import { ApiError, api } from "@/api/client";
import { useSession } from "@/auth/session";
import { PrimaryButton, ScreenScaffold, SectionSurface, TextField } from "@/design-system";

export default function ParentLoginRoute() {
  const router = useRouter();
  const { signIn } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const submit = async () => {
    try { await signIn(await api.login(email, password)); router.replace("/parent/home"); }
    catch (error) { setMessage(error instanceof ApiError ? error.message : "Login failed."); }
  };
  return (
    <ScreenScaffold title="Parent sign in">
      <SectionSurface>
        <TextField label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" />
        <TextField label="Password" value={password} onChangeText={setPassword} secureTextEntry />
        {message ? <Text accessibilityRole="alert">{message}</Text> : null}
        <PrimaryButton label="Sign in" onPress={submit} disabled={!email || !password} />
        <Link href="/parent/signup">Create a parent account</Link>
      </SectionSurface>
    </ScreenScaffold>
  );
}
