const JSON_HEADERS = {
  "Content-Type": "application/json",
  Accept: "application/json",
};

export async function login(membershipId, password) {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({
      membership_id: membershipId,
      password,
    }),
  });
  if (!response.ok) throw new Error("login failed");
  return response.json();
}

export async function fetchPage(slug) {
  const response = await fetch(`/api/pages/${slug}`);
  if (!response.ok) throw new Error("page failed");
  return response.json();
}

export async function saveMember(blocks) {
  const token = sessionStorage.getItem("koc10930.token");
  const response = await fetch("/api/pages/member", {
    method: "PUT",
    headers: {
      ...JSON_HEADERS,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ blocks }),
  });
  if (!response.ok) throw new Error("save failed");
  return response.json();
}
