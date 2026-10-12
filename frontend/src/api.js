const JSON_HEADERS = {
  "Content-Type": "application/json",
  Accept: "application/json",
};

export const authBus = new EventTarget();

let refreshPromise = null;

function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = fetch("/api/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/json" },
    })
      .then((response) => response.ok)
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function errorMessage(response, fallback) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    /* The response had no JSON body. */
  }
  return fallback;
}

export async function login(memberid, password) {
  let response;
  try {
    response = await fetch("/api/auth/login", {
      method: "POST",
      credentials: "include",
      headers: JSON_HEADERS,
      body: JSON.stringify({ memberid, password }),
    });
  } catch {
    throw new Error("The sign-in service is unavailable.");
  }
  if (response.status === 422) {
    throw new Error("Enter a numeric membership ID and password.");
  }
  if (!response.ok) {
    throw new Error(await errorMessage(response, "Sign in failed."));
  }
  return response.json();
}

export async function logout() {
  sessionStorage.removeItem("koc10930.token");
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    });
  } catch {
    /* The local session is cleared even if the API is down. */
  }
}

export async function currentMember() {
  let response = await fetch("/api/auth/me", {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (response.status === 401) {
    const refreshed = await refreshSession();
    if (!refreshed) return null;
    response = await fetch("/api/auth/me", {
      credentials: "include",
      headers: { Accept: "application/json" },
    });
  }
  if (response.status === 401) return null;
  if (!response.ok) throw new Error("session failed");
  return response.json();
}

async function send(path, options = {}, retry = true) {
  const response = await fetch(path, {
    credentials: "include",
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });
  if (response.status === 401 && retry) {
    const refreshed = await refreshSession();
    if (refreshed) return send(path, options, false);
    authBus.dispatchEvent(new Event("expired"));
  }
  return response;
}

export async function fetchPage(slug) {
  const response = await send(`/api/pages/${slug}`, {}, slug === "member");
  if (!response.ok) throw new Error("page failed");
  return response.json();
}

export async function saveMember(blocks) {
  const response = await send("/api/pages/member", {
    method: "PUT",
    body: JSON.stringify({ blocks }),
  });
  if (!response.ok) throw new Error("save failed");
  return response.json();
}
