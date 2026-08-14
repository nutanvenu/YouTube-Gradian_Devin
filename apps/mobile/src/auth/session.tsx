import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";
import { api, Parent, sessionStorage, Tokens } from "@/api/client";

type SessionContextValue = {
  parent: Parent | null;
  loading: boolean;
  familyId: string | null;
  signIn: (tokens: Tokens) => Promise<void>;
  setFamilyId: (familyId: string) => Promise<void>;
  signOut: () => Promise<void>;
};
const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: PropsWithChildren) {
  const [parent, setParent] = useState<Parent | null>(null);
  const [loading, setLoading] = useState(true);
  const [familyId, setFamilyIdState] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([sessionStorage.getAccessToken(), sessionStorage.getFamilyId()])
      .then(async ([token, storedFamilyId]) => {
        setFamilyIdState(storedFamilyId);
        if (!token) return null;
        const currentParent = await api.me();
        if (!storedFamilyId) {
          const families = await api.families();
          if (families[0]) {
            await sessionStorage.setFamilyId(families[0].id);
            setFamilyIdState(families[0].id);
          }
        }
        return currentParent;
      })
      .then(setParent)
      .catch(() => sessionStorage.clear())
      .finally(() => setLoading(false));
  }, []);
  const value = useMemo(() => ({
    parent,
    loading,
    familyId,
    signIn: async (tokens: Tokens) => { await sessionStorage.setTokens(tokens); setParent(await api.me()); },
    setFamilyId: async (nextFamilyId: string) => { await sessionStorage.setFamilyId(nextFamilyId); setFamilyIdState(nextFamilyId); },
    signOut: async () => { await sessionStorage.clear(); setParent(null); },
  }), [familyId, loading, parent]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used within SessionProvider");
  return value;
}
