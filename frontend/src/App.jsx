import { useEffect } from "react";
import { useAuth } from "./auth/AuthContext";
import LoginPage from "./pages/LoginPage";
import MemberPage from "./pages/MemberPage";
import PublicPage from "./pages/PublicPage";
import { navigate, usePath } from "./router";

function MemberGate() {
  const { user, ready } = useAuth();

  useEffect(() => {
    if (!ready || user) return;
    const next = `${window.location.pathname}${window.location.search}`;
    navigate(`/login?next=${encodeURIComponent(next)}`);
  }, [ready, user]);

  if (!ready) return <p className="auth-gate">Checking your session…</p>;
  if (!user) return null;
  return <MemberPage />;
}

export default function App() {
  const path = usePath();
  if (path === "/login") return <LoginPage />;
  if (path === "/member" || path.startsWith("/member/")) return <MemberGate />;
  return <PublicPage />;
}
