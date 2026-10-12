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
  const isForm = typeof FormData !== "undefined" && options.body instanceof FormData;
  const response = await fetch(path, {
    credentials: "include",
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body && !isForm ? { "Content-Type": "application/json" } : {}),
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
  if (!response.ok) throw new Error(await errorMessage(response, "save failed"));
  return response.json();
}

export function imageFileError(file) {
  if (!file) return "Choose an image file.";
  const ext = file.name.includes(".") ? file.name.split(".").pop().toLowerCase() : "";
  if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
    return "Only JPG, PNG, and WebP images are accepted.";
  }
  if (file.size > 8 * 1024 * 1024) return "Image must be 8 MB or smaller.";
  return "";
}

async function readJson(response, fallback) {
  if (!response.ok) throw new Error(await errorMessage(response, fallback));
  if (response.status === 204) return null;
  return response.json();
}

export async function updateMyTitle(title) {
  const response = await send("/api/members/me", {
    method: "PATCH",
    body: JSON.stringify({ title: title || null }),
  });
  return readJson(response, "Could not save the title.");
}

export async function uploadMyPhoto(file) {
  const body = new FormData();
  body.append("file", file);
  const response = await send("/api/members/me/photo", { method: "POST", body });
  return readJson(response, "Could not upload the photo.");
}

export async function deleteMyPhoto() {
  const response = await send("/api/members/me/photo", { method: "DELETE" });
  return readJson(response, "Could not remove the photo.");
}

export async function fetchMembers() {
  const response = await send("/api/members");
  return readJson(response, "Could not load members.");
}

export async function setMemberAdmin(memberid, isAdmin) {
  const response = await send(`/api/members/${encodeURIComponent(memberid)}`, {
    method: "PATCH",
    body: JSON.stringify({ is_admin: isAdmin }),
  });
  return readJson(response, "Could not update admin access.");
}

export async function fetchMediaSlots() {
  const response = await fetch("/api/media/slots", { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("media failed");
  return response.json();
}

export async function fetchMedia() {
  const response = await send("/api/media");
  return readJson(response, "Could not load images.");
}

export async function uploadMedia(file) {
  const body = new FormData();
  body.append("file", file);
  const response = await send("/api/media", { method: "POST", body });
  return readJson(response, "Could not upload the image.");
}

export async function replaceMedia(id, file) {
  const body = new FormData();
  body.append("file", file);
  const response = await send(`/api/media/${id}/replace`, { method: "POST", body });
  return readJson(response, "Could not replace the image.");
}

export async function deleteMedia(id) {
  const response = await send(`/api/media/${id}`, { method: "DELETE" });
  return readJson(response, "Could not remove the image.");
}

export async function assignMediaSlot(id, slot) {
  const response = await send(`/api/media/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ slot: slot || null }),
  });
  return readJson(response, "Could not update the image slot.");
}
