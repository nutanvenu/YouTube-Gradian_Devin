import { useState } from "react";
import { useRouter } from "expo-router";
import { Text } from "react-native";
import { ApiError, api } from "@/api/client";
import { useSession } from "@/auth/session";
import { PrimaryButton, ScreenScaffold, SectionSurface, TextField } from "@/design-system";

export default function ParentSignupRoute() {
  const router = useRouter();
  const { signIn } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const submit = async () => {
    try { await signIn(await api.signup(email, password)); router.replace("/parent/setup"); }
    catch (error) { setMessage(error instanceof ApiError ? error.message : "Signup failed."); }
  };
  return (
    <ScreenScaffold title="Create parent account">
      <SectionSurface>
        <TextField label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" />
        <TextField label="Password" value={password} onChangeText={setPassword} secureTextEntry />
        <Text>Password must meet Guardian's password requirements.</Text>
        {message ? <Text accessibilityRole="alert">{message}</Text> : null}
        <PrimaryButton label="Create account" onPress={submit} disabled={!email || password.length < 12} />
      </SectionSurface>
    </ScreenScaffold>
  );
}
