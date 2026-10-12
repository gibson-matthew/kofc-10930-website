import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { authBus, currentMember, login as loginRequest, logout as logoutRequest } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancel = false;
    currentMember()
      .then((member) => {
        if (!cancel) setUser(member);
      })
      .catch(() => {
        if (!cancel) setUser(null);
      })
      .finally(() => {
        if (!cancel) setReady(true);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    const onExpired = () => setUser(null);
    authBus.addEventListener("expired", onExpired);
    return () => authBus.removeEventListener("expired", onExpired);
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      async login(memberid, password) {
        const member = await loginRequest(memberid, password);
        setUser(member);
        return member;
      },
      async logout() {
        try {
          await logoutRequest();
        } finally {
          setUser(null);
        }
      },
    }),
    [user, ready],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("Auth is unavailable");
  return value;
}
