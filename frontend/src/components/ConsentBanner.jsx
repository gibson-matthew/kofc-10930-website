import { useEffect, useState } from "react";
import { consentChoice, flush, saveConsent, track } from "../tracking";

export function PageView({ path }) {
  useEffect(() => {
    const started = Date.now();
    let sent = false;
    function leave() {
      if (sent) return;
      sent = true;
      const seconds = Math.max(0, Math.min(86400, Math.round((Date.now() - started) / 1000)));
      track("page.leave", { path, duration_seconds: seconds });
      flush();
    }
    track("page.view", { path });
    window.addEventListener("pagehide", leave);
    return () => {
      window.removeEventListener("pagehide", leave);
      leave();
    };
  }, [path]);
  return null;
}

export default function ConsentBanner() {
  const [choice, setChoice] = useState(() => consentChoice());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    document.body.classList.toggle("has-consent-banner", !choice);
    return () => document.body.classList.remove("has-consent-banner");
  }, [choice]);

  if (choice) return null;

  async function choose(next) {
    setPending(true);
    setError("");
    try {
      await saveConsent(next);
      setChoice(next);
      if (next === "accepted") track("page.view", { path: window.location.pathname });
    } catch {
      setError("Your choice was not saved. You can still use the site and try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="consent-banner" role="region" aria-label="Optional cookies">
      <div className="consent-banner-inner">
        <div>
          <p>
            We use essential cookies to keep you signed in and secure. Optional cookies help us understand how the
            site is used so we can improve it. You can decline optional tracking and still use the site.
          </p>
          {error ? <p className="consent-note">{error}</p> : null}
        </div>
        <div className="consent-actions">
          <button type="button" className="btn" disabled={pending} onClick={() => choose("accepted")}>
            Accept
          </button>
          <button type="button" className="btn btn-quiet" disabled={pending} onClick={() => choose("declined")}>
            Decline
          </button>
        </div>
      </div>
    </div>
  );
}
