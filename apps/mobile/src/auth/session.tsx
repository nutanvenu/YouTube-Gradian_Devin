import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";
import { api, ApiError, Parent, sessionStorage, subscribeToParentSessionExpiry, Tokens } from "@/api/client";

type SessionContextValue = {
  parent: Parent | null;
  loading: boolean;
  familyId: string | null;
  sessionError: "SESSION_EXPIRED" | null;
  signIn: (tokens: Tokens) => Promise<void>;
  setFamilyId: (familyId: string) => Promise<void>;
  signOut: () => Promise<void>;
};
const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: PropsWithChildren) {
  const [parent, setParent] = useState<Parent | null>(null);
  const [loading, setLoading] = useState(true);
  const [familyId, setFamilyIdState] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<"SESSION_EXPIRED" | null>(null);
  useEffect(
    () => subscribeToParentSessionExpiry(() => {
      // The API client has already removed parent credentials.  Do not touch
      // the paired child device credentials: child protection continues.
      setParent(null);
      setSessionError("SESSION_EXPIRED");
    }),
    [],
  );
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
      .catch(async (error: unknown) => {
        await sessionStorage.clearParentSession();
        setParent(null);
        setSessionError(error instanceof ApiError && error.code === "SESSION_EXPIRED" ? "SESSION_EXPIRED" : null);
      })
      .finally(() => setLoading(false));
  }, []);
  const value = useMemo(() => ({
    parent,
    loading,
    familyId,
    sessionError,
    signIn: async (tokens: Tokens) => {
      await sessionStorage.setTokens(tokens);
      setParent(await api.me());
      setSessionError(null);
    },
    setFamilyId: async (nextFamilyId: string) => { await sessionStorage.setFamilyId(nextFamilyId); setFamilyIdState(nextFamilyId); },
    signOut: async () => { await sessionStorage.clearParentSession(); setParent(null); setSessionError(null); },
  }), [familyId, loading, parent, sessionError]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used within SessionProvider");
  return value;
}
