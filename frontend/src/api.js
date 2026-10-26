const JSON_HEADERS = {
  "Content-Type": "application/json",
  Accept: "application/json",
};

export function apiUrl(path) {
  const value = String(path || "");
  if (/^https?:\/\//i.test(value)) return value;
  const base = String(import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");
  const suffix = value.startsWith("/") ? value : `/${value}`;
  return `${base}${suffix}`;
}

export function mediaUrl(src) {
  const value = String(src || "");
  if (!value || /^(https?:|blob:|data:)/i.test(value)) return value;
  if (value.startsWith("/api/") || value.startsWith("api/")) {
    return apiUrl(value.startsWith("/") ? value : `/${value}`);
  }
  return value;
}

export const authBus = new EventTarget();

let refreshPromise = null;

function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = fetch(apiUrl("/api/auth/refresh"), {
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
    response = await fetch(apiUrl("/api/auth/login"), {
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
    await fetch(apiUrl("/api/auth/logout"), {
      method: "POST",
      credentials: "include",
    });
  } catch {
    /* The local session is cleared even if the API is down. */
  }
}

export async function currentMember() {
  let response = await fetch(apiUrl("/api/auth/me"), {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (response.status === 401) {
    const refreshed = await refreshSession();
    if (!refreshed) return null;
    response = await fetch(apiUrl("/api/auth/me"), {
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
  const response = await fetch(apiUrl(path), {
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

export async function uploadMyPhoto(file, crop = {}) {
  const body = new FormData();
  body.append("file", file);
  body.append("crop_x", String(crop.x ?? crop.crop_x ?? 0));
  body.append("crop_y", String(crop.y ?? crop.crop_y ?? 0));
  body.append("crop_scale", String(crop.scale ?? crop.crop_scale ?? 1));
  const response = await send("/api/members/me/photo", { method: "POST", body });
  return readJson(response, "Could not upload the photo.");
}

export async function updateMyCrop(crop) {
  const response = await send("/api/members/me/photo", {
    method: "PATCH",
    body: JSON.stringify({
      crop_x: crop.x ?? crop.crop_x ?? 0,
      crop_y: crop.y ?? crop.crop_y ?? 0,
      crop_scale: crop.scale ?? crop.crop_scale ?? 1,
    }),
  });
  return readJson(response, "Could not save the viewing angle.");
}

export async function assignPastGrandKnight(memberid, fields) {
  const response = await send(`/api/members/${encodeURIComponent(memberid)}/pgk`, {
    method: "POST",
    body: JSON.stringify({
      period: fields.period || "",
      note: fields.note || "",
    }),
  });
  return readJson(response, "Could not save Past Grand Knight.");
}

export async function setMemberTitle(memberid, title) {
  const response = await send(`/api/members/${encodeURIComponent(memberid)}/title`, {
    method: "PATCH",
    body: JSON.stringify({ title: title || null }),
  });
  return readJson(response, "Could not save the title.");
}

export async function fetchRoster() {
  const response = await send("/api/members/roster");
  return readJson(response, "Could not load members.");
}

export async function fetchDirectory() {
  let response;
  try {
    response = await send("/api/members/directory");
  } catch {
    throw new Error("Could not load members.");
  }
  return readJson(response, "Could not load members.");
}

export async function setMemberHonorary(memberid, honorary) {
  const response = await send(`/api/members/${encodeURIComponent(memberid)}/honorary`, {
    method: "PATCH",
    body: JSON.stringify({ honorary_life: Boolean(honorary) }),
  });
  return readJson(response, "Could not update Honorary Life Member.");
}

export async function saveRoleAssignments(payload) {
  const response = await send("/api/members/assignments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return readJson(response, "Could not save officer assignments.");
}

export async function deleteMyPhoto() {
  const response = await send("/api/members/me/photo", { method: "DELETE" });
  return readJson(response, "Could not remove the photo.");
}

export async function fetchMembers() {
  const response = await send("/api/members");
  return readJson(response, "Could not load members.");
}

export async function fetchActivity(filters = {}) {
  const params = new URLSearchParams();
  if (filters.event_type) params.set("event_type", filters.event_type);
  if (filters.member_id) params.set("member_id", filters.member_id);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.q) params.set("q", filters.q);
  const query = params.toString();
  const response = await send(`/api/audit/log${query ? `?${query}` : ""}`);
  return readJson(response, "Could not load activity.");
}

export async function setMemberBirthday(memberid, payload) {
  const response = await send(`/api/members/${encodeURIComponent(memberid)}/birthday`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return readJson(response, "Could not save the birthday.");
}

export async function setMemberAdmin(memberid, isAdmin) {
  const response = await send(`/api/members/${encodeURIComponent(memberid)}`, {
    method: "PATCH",
    body: JSON.stringify({ is_admin: isAdmin }),
  });
  return readJson(response, "Could not update admin access.");
}

export async function setMemberWebmaster(memberid, isWebmaster) {
  const response = await send(`/api/members/${encodeURIComponent(memberid)}/webmaster`, {
    method: "PATCH",
    body: JSON.stringify({ is_webmaster: isWebmaster }),
  });
  return readJson(response, "Could not update webmaster access.");
}

export async function fetchMediaSlots() {
  const response = await fetch(apiUrl("/api/media/slots"), { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("media failed");
  return response.json();
}

export async function fetchMedia() {
  const response = await send("/api/media");
  return readJson(response, "Could not load images.");
}

function appendCrop(body, crop) {
  if (!crop) return;
  body.append("crop_x", String(crop.x ?? crop.crop_x ?? 0));
  body.append("crop_y", String(crop.y ?? crop.crop_y ?? 0));
  body.append("crop_scale", String(crop.scale ?? crop.crop_scale ?? 1));
}

export async function uploadMedia(file, crop) {
  const body = new FormData();
  body.append("file", file);
  appendCrop(body, crop);
  const response = await send("/api/media", { method: "POST", body });
  return readJson(response, "Could not upload the image.");
}

export async function replaceMedia(id, file, crop) {
  const body = new FormData();
  body.append("file", file);
  appendCrop(body, crop);
  const response = await send(`/api/media/${id}/replace`, { method: "POST", body });
  return readJson(response, "Could not replace the image.");
}

export async function updateMediaCrop(id, crop) {
  const response = await send(`/api/media/${id}/crop`, {
    method: "PATCH",
    body: JSON.stringify({
      crop_x: crop.x ?? crop.crop_x ?? 0,
      crop_y: crop.y ?? crop.crop_y ?? 0,
      crop_scale: crop.scale ?? crop.crop_scale ?? 1,
    }),
  });
  return readJson(response, "Could not save the viewing angle.");
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

export async function createMember(payload) {
  const response = await send("/api/members", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return readJson(response, "Could not create the member.");
}

export async function fetchHonors() {
  const response = await send("/api/honors");
  return readJson(response, "Could not load past honors.");
}

function honorBody(fields, file) {
  const body = new FormData();
  body.append("category", fields.category);
  body.append("name", fields.name || "");
  body.append("note", fields.note || "");
  body.append("year", fields.year == null ? "" : String(fields.year));
  body.append("month", fields.month == null ? "" : String(fields.month));
  body.append("period", fields.period || "");
  if (fields.clear_photo) body.append("clear_photo", "true");
  appendCrop(body, fields.crop || { x: 0, y: 0, scale: 1 });
  if (file) body.append("file", file);
  return body;
}

export async function createHonor(fields, file) {
  const response = await send("/api/honors", { method: "POST", body: honorBody(fields, file) });
  return readJson(response, "Could not add the past honor.");
}

export async function updateHonor(id, fields, file) {
  const response = await send(`/api/honors/${id}`, { method: "PATCH", body: honorBody(fields, file) });
  return readJson(response, "Could not save the past honor.");
}

export async function deleteHonor(id) {
  const response = await send(`/api/honors/${id}`, { method: "DELETE" });
  return readJson(response, "Could not remove the past honor.");
}

export async function fetchEvents() {
  const response = await send("/api/events");
  return readJson(response, "Could not load events.");
}

export async function createEvent(payload) {
  const response = await send("/api/events", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return readJson(response, "Could not add the event.");
}

export async function updateEvent(id, payload) {
  const response = await send(`/api/events/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return readJson(response, "Could not save the event.");
}

export async function deleteEvent(id) {
  const response = await send(`/api/events/${id}`, { method: "DELETE" });
  return readJson(response, "Could not remove the event.");
}

const DOCUMENT_EXTENSIONS = ["pdf", "doc", "docx", "xls", "xlsx"];

export const DOCUMENT_ACCEPT =
  ".pdf,.doc,.docx,.xls,.xlsx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

export function documentFileError(file) {
  if (!file) return "Choose a document.";
  const ext = file.name.includes(".") ? file.name.split(".").pop().toLowerCase() : "";
  if (!DOCUMENT_EXTENSIONS.includes(ext)) {
    return "Only PDF, DOC, DOCX, XLS, and XLSX files are accepted.";
  }
  if (file.size > 16 * 1024 * 1024) return "Document must be 16 MB or smaller.";
  return "";
}

export function documentFileUrl(id) {
  return apiUrl(`/api/documents/${id}/file`);
}

export async function fetchDocuments(library) {
  let response;
  try {
    response = await send(`/api/documents?library=${encodeURIComponent(library)}`);
  } catch {
    throw new Error("Could not load documents.");
  }
  return readJson(response, "Could not load documents.");
}

export async function uploadDocument(library, fields, file) {
  const body = new FormData();
  body.append("library", library);
  body.append("title", fields.title || "");
  body.append("description", fields.description || "");
  body.append("file", file);
  const response = await send("/api/documents", { method: "POST", body });
  return readJson(response, "Could not add the document.");
}

export async function deleteDocument(id) {
  const response = await send(`/api/documents/${id}`, { method: "DELETE" });
  return readJson(response, "Could not remove the document.");
}

export async function fetchAnnouncements() {
  let response;
  try {
    response = await send("/api/announcements");
  } catch {
    throw new Error("Could not load announcements.");
  }
  return readJson(response, "Could not load announcements.");
}

export async function fetchAnnouncement(id) {
  const response = await send(`/api/announcements/${encodeURIComponent(id)}`);
  return readJson(response, "Could not load the announcement.");
}

export async function saveAnnouncement(fields, id) {
  const response = await send(id ? `/api/announcements/${encodeURIComponent(id)}` : "/api/announcements", {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify({
      title: fields.title || "",
      summary: fields.summary || "",
      body: fields.body || "",
    }),
  });
  return readJson(response, "Could not save the announcement.");
}

export async function deleteAnnouncement(id) {
  const response = await send(`/api/announcements/${encodeURIComponent(id)}`, { method: "DELETE" });
  return readJson(response, "Could not remove the announcement.");
}

export async function fetchPrayers() {
  let response;
  try {
    response = await send("/api/prayers");
  } catch {
    throw new Error("Could not load prayer requests.");
  }
  return readJson(response, "Could not load prayer requests.");
}

export async function savePrayer(fields, id) {
  const response = await send(id ? `/api/prayers/${encodeURIComponent(id)}` : "/api/prayers", {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify({
      title: fields.title || "",
      body: fields.body || "",
    }),
  });
  return readJson(response, "Could not save the prayer request.");
}

export async function deletePrayer(id) {
  const response = await send(`/api/prayers/${encodeURIComponent(id)}`, { method: "DELETE" });
  return readJson(response, "Could not remove the prayer request.");
}

export async function fetchNominations() {
  let response;
  try {
    response = await send("/api/nominations");
  } catch {
    throw new Error("Could not load nominations.");
  }
  return readJson(response, "Could not load nominations.");
}

export async function fetchNominationResults() {
  let response;
  try {
    response = await send("/api/nominations/results");
  } catch {
    throw new Error("Could not load nomination results.");
  }
  return readJson(response, "Could not load nomination results.");
}

export async function saveNomination(fields) {
  const response = await send("/api/nominations", {
    method: "POST",
    body: JSON.stringify({
      category: fields.category || "",
      nominee_member_id: fields.nominee_member_id || "",
      nominee_name: fields.nominee_name || "",
      reason: fields.reason || "",
    }),
  });
  return readJson(response, "Could not save the nomination.");
}

export async function withdrawNomination(id) {
  const response = await send(`/api/nominations/${encodeURIComponent(id)}`, { method: "DELETE" });
  return readJson(response, "Could not withdraw the nomination.");
}
