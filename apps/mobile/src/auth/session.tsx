import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";
import { api, Parent, sessionStorage, Tokens } from "@/api/client";

type SessionContextValue = { parent: Parent | null; loading: boolean; signIn: (tokens: Tokens) => Promise<void>; signOut: () => Promise<void> };
const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: PropsWithChildren) {
  const [parent, setParent] = useState<Parent | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    sessionStorage.getAccessToken().then((token) => (token ? api.me() : null)).then(setParent).catch(() => sessionStorage.clear()).finally(() => setLoading(false));
  }, []);
  const value = useMemo(() => ({
    parent,
    loading,
    signIn: async (tokens: Tokens) => { await sessionStorage.setTokens(tokens); setParent(await api.me()); },
    signOut: async () => { await sessionStorage.clear(); setParent(null); },
  }), [loading, parent]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used within SessionProvider");
  return value;
}
