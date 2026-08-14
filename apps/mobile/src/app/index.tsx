import { useEffect, useState } from "react";
import { Redirect } from "expo-router";
import { roleStorage, Role } from "@/state/role";
import { DataState } from "@/design-system";

export default function IndexRoute() {
  const [role, setRole] = useState<Role | null | undefined>(undefined);
  useEffect(() => { roleStorage.get().then(setRole); }, []);
  if (role === undefined) return <DataState state="initial" />;
  if (role === "parent") return <Redirect href="/parent/login" />;
  if (role === "child") return <Redirect href="/child/pair" />;
  return <Redirect href="/role-selection" />;
}
