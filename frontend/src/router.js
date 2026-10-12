import { useEffect, useState } from "react";

const bus = new EventTarget();

export function navigate(to) {
  const url = new URL(to, window.location.origin);
  const next = `${url.pathname}${url.search}${url.hash}`;
  const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  if (current !== next) {
    window.history.pushState({}, "", next);
  }
  window.scrollTo(0, 0);
  bus.dispatchEvent(new Event("nav"));
}

export function safeNext(fallback = "/member") {
  const next = new URLSearchParams(window.location.search).get("next");
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return fallback;
  }
  if (next === "/login" || next.startsWith("/login/") || next.startsWith("/login?")) {
    return fallback;
  }
  return next;
}

export function usePath() {
  const [path, setPath] = useState(() => window.location.pathname);

  useEffect(() => {
    const sync = () => setPath(window.location.pathname);
    bus.addEventListener("nav", sync);
    window.addEventListener("popstate", sync);
    return () => {
      bus.removeEventListener("nav", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);

  return path;
}
