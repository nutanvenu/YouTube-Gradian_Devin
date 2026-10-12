import { Redirect, Stack, useSegments } from "expo-router";
import { useSession } from "@/auth/session";
import { DataState } from "@/design-system";

export default function ParentLayout() {
  const { parent, loading } = useSession();
  const segments = useSegments();
  const publicRoute = ["login", "signup", "forgot-password", "reset-password", "verify-email"].includes(segments[segments.length - 1] ?? "");
  if (loading) return <DataState state="loading" />;
  if (!parent && !publicRoute) return <Redirect href="/parent/login" />;
  return <Stack screenOptions={{ headerShown: false }} />;
}
