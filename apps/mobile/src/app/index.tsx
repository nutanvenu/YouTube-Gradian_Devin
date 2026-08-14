import { useEffect, useState } from "react";
import { Redirect } from "expo-router";
import { sessionStorage } from "@/api/client";
import { roleStorage, Role } from "@/state/role";
import { DataState } from "@/design-system";

export default function IndexRoute() {
  const [role, setRole] = useState<Role | null | undefined>(undefined);
  const [hasDevice, setHasDevice] = useState<boolean | undefined>(undefined);
  useEffect(() => {
    void Promise.all([roleStorage.get(), sessionStorage.getDeviceToken()]).then(([storedRole, deviceToken]) => {
      setRole(storedRole);
      setHasDevice(Boolean(deviceToken));
    });
  }, []);
  if (role === undefined || hasDevice === undefined) return <DataState state="initial" />;
  if (role === "parent") return <Redirect href="/parent/login" />;
  if (role === "child") return <Redirect href={hasDevice ? "/child/home" : "/child/pair"} />;
  return <Redirect href="/role-selection" />;
}
