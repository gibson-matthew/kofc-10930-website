import { useEffect, useState } from "react";

const bus = new EventTarget();

export function navigate(to) {
  if (window.location.pathname !== to) {
    window.history.pushState({}, "", to);
  }
  window.scrollTo(0, 0);
  bus.dispatchEvent(new Event("nav"));
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
