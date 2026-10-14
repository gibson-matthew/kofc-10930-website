import { useEffect, useLayoutEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { ContentProvider, useContent } from "../content/ContentContext";
import { SITE_TITLE } from "../content/seed";
import { navigate, safeNext } from "../router";

const TITLE = SITE_TITLE;

function LoginForm() {
  const { text } = useContent();
  const { user, ready, login } = useAuth();
  const [memberid, setMemberid] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const destination = safeNext();

  useLayoutEffect(() => {
    document.body.className = "page-login";
    document.body.dataset.page = "login";
    document.title = TITLE;
  }, []);

  useEffect(() => {
    if (ready && user) navigate(destination);
  }, [ready, user, destination]);

  async function onSubmit(event) {
    event.preventDefault();
    if (pending) return;
    setError("");
    const id = memberid.trim();
    if (!id || !password) {
      setError("Enter your membership ID and password.");
      return;
    }
    setPending(true);
    try {
      await login(id, password);
      navigate(destination);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed.");
      setPending(false);
    }
  }

  if (!ready || user) {
    return <p className="auth-gate">Checking your session…</p>;
  }

  return (
    <main className="login-screen">
      <div className="signin-dialog login-card">
        <h1 id="signInTitle">{text("signin.title") || "Member sign in"}</h1>
        <form id="signInForm" onSubmit={onSubmit}>
          {error ? (
            <p className="signin-error" role="alert">
              {error}
            </p>
          ) : null}
          <label className="signin-field">
            <span>{text("signin.membership") || "Membership ID"}</span>
            <input
              type="text"
              name="memberid"
              inputMode="numeric"
              autoComplete="username"
              autoCapitalize="off"
              spellCheck={false}
              required
              value={memberid}
              onChange={(event) => setMemberid(event.target.value)}
            />
          </label>
          <label className="signin-field">
            <span>{text("signin.password") || "Password"}</span>
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <div className="signin-actions">
            <button type="button" className="btn btn-quiet" onClick={() => navigate("/")}>
              {text("signin.cancel") || "Cancel"}
            </button>
            <button type="submit" className="btn" disabled={pending}>
              {pending ? "Signing in…" : text("signin.submit") || "Sign in"}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <ContentProvider slug="public">
      <LoginForm />
    </ContentProvider>
  );
}
