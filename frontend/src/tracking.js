const CONSENT_VERSION = "1";
const CONSENT_COOKIE = "koc_consent";

let queue = [];
let flushTimer = 0;
const searchTimers = new Map();
const lastSearch = new Map();

function collapse(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

export function consentChoice() {
  const match = document.cookie.match(new RegExp(`(?:^|; )${CONSENT_COOKIE}=([^;]*)`));
  if (!match) return null;
  const [version, choice, stamp] = decodeURIComponent(match[1]).split(".");
  if (version !== CONSENT_VERSION || (choice !== "accepted" && choice !== "declined") || !/^\d+$/.test(stamp || "")) {
    return null;
  }
  return choice;
}

export async function saveConsent(choice) {
  const response = await fetch("/api/consent", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ choice }),
  });
  if (!response.ok) throw new Error("consent failed");
  return response.json();
}

function scheduleFlush() {
  if (flushTimer) return;
  flushTimer = window.setTimeout(flush, 400);
}

export function flush() {
  if (flushTimer) window.clearTimeout(flushTimer);
  flushTimer = 0;
  if (!queue.length) return;
  const events = queue.splice(0, 20);
  const body = JSON.stringify({
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
    language: navigator.language || "",
    events,
  });
  fetch("/api/audit/events", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => {});
}

export function track(type, details) {
  const necessary = type === "error.frontend";
  if (!necessary && consentChoice() !== "accepted") return;
  queue.push({ type, details: details || {} });
  if (queue.length > 40) queue = queue.slice(-40);
  scheduleFlush();
}

export function trackClick(name, details) {
  track("ui.click", { name, ...(details || {}) });
}

export function trackFeature(feature, details) {
  track("feature.use", { feature, ...(details || {}) });
}

export function watchSearch(scope, query, resultCount) {
  const cleaned = collapse(query);
  const pending = searchTimers.get(scope);
  if (!cleaned) {
    if (pending) window.clearTimeout(pending);
    searchTimers.delete(scope);
    lastSearch.delete(scope);
    return;
  }
  const signature = `${cleaned}|${resultCount}`;
  if (lastSearch.get(scope) === signature) return;
  if (pending) window.clearTimeout(pending);
  searchTimers.set(
    scope,
    window.setTimeout(() => {
      lastSearch.set(scope, signature);
      track("search.query", {
        scope,
        query: cleaned.slice(0, 120),
        result_count: resultCount,
        used: false,
      });
    }, 700),
  );
}

export function trackSearchUse(scope, query, details) {
  const cleaned = collapse(query);
  if (!cleaned) return;
  track("search.use", {
    scope,
    query: cleaned.slice(0, 120),
    used: true,
    ...(details || {}),
  });
}

export function installFrontendErrors() {
  window.addEventListener("error", (event) => {
    track("error.frontend", { message: String(event?.message || "Script error").slice(0, 300) });
    flush();
  });
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event?.reason;
    const message = reason instanceof Error ? reason.message : "Unhandled error";
    track("error.frontend", { message: String(message).slice(0, 300) });
    flush();
  });
}
