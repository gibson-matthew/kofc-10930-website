import { useEffect } from "react";
import { useAuth } from "./auth/AuthContext";
import ConsentBanner, { PageView } from "./components/ConsentBanner";
import LoginPage from "./auth/LoginPage";
import MemberPage from "./member/MemberPage";
import PublicPage from "./public/PublicPage";
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
  let page = <PublicPage />;
  if (path === "/login") page = <LoginPage />;
  else if (path === "/member" || path.startsWith("/member/")) page = <MemberGate />;
  return (
    <>
      <PageView path={path} />
      {page}
      <ConsentBanner />
    </>
  );
}
