// Shared API helper: stores the JWT in localStorage and attaches it to
// every request. A 401 anywhere means the token is missing/expired, so we
// bounce to the login page rather than showing a broken authenticated view.

const TOKEN_KEY = "smartstock_token";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "/login";
  }
}

async function apiFetch(path, options = {}) {
  const headers = options.headers || {};
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (options.body && !(options.body instanceof URLSearchParams)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(path, { ...options, headers });

  if (response.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  return response;
}

async function apiGet(path) {
  const response = await apiFetch(path);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

async function apiPost(path, data) {
  const response = await apiFetch(path, {
    method: "POST",
    body: data !== undefined ? JSON.stringify(data) : undefined,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function apiDelete(path) {
  const response = await apiFetch(path, { method: "DELETE" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return null;
}

function logout() {
  clearToken();
  window.location.href = "/login";
}

function formatMoney(value) {
  if (value === null || value === undefined) return "—";
  return "₹" + Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatPercent(value) {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(2)}%`;
}

function pnlClass(value) {
  if (value === null || value === undefined) return "neutral";
  return value >= 0 ? "positive" : "negative";
}

// Escape text before inserting into innerHTML. Required for ANY externally
// sourced content (news headlines/sources from Google News RSS are the
// clearest example) — without this, a malicious headline could inject a
// <script> that reads the JWT out of localStorage. Our own DB-controlled
// values (stock symbols/names we seeded) are lower risk but escaped anyway
// as defense in depth.
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text === null || text === undefined ? "" : String(text);
  return div.innerHTML;
}

// Only allow http(s) URLs into an href we build via string interpolation —
// rejects javascript: URIs and escapes quotes so the value can't break out
// of the attribute.
function safeUrl(url) {
  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return "#";
    return escapeHtml(parsed.href);
  } catch {
    return "#";
  }
}
