import { API_BASE } from "./config.js";
import { currentLang } from "./i18n.js";

const store = {
  get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  del(k) { try { localStorage.removeItem(k); } catch {} },
};
export { store };

export const auth = {
  get tokens() { return store.get("apteka.tokens"); },
  get user() { return store.get("apteka.user"); },
  save(tokens, user) { store.set("apteka.tokens", tokens); if (user) store.set("apteka.user", user); },
  setUser(user) { store.set("apteka.user", user); },
  clear() { store.del("apteka.tokens"); store.del("apteka.user"); },
};

export class ApiError extends Error {
  constructor(status, data) {
    const text = data && (data.detail || Object.values(data).flat().join(" "));
    super(text || (status === 0 ? "Network" : `Error ${status}`));
    this.status = status; this.data = data;
  }
}

async function refreshAccess() {
  const t = auth.tokens;
  if (!t?.refresh) return false;
  const r = await fetch(`${API_BASE}/api/auth/refresh/`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh: t.refresh }),
  });
  if (!r.ok) { auth.clear(); return false; }
  const data = await r.json();
  auth.save({ ...t, access: data.access });
  return true;
}

export async function api(path, { method = "GET", body, query, form, retry = true } = {}) {
  let url = `${API_BASE}/api${path}`;
  if (query) url += "?" + new URLSearchParams(Object.entries(query).filter(([, v]) => v !== undefined && v !== null));
  const headers = { "Accept-Language": currentLang() };
  if (!form) headers["Content-Type"] = "application/json";
  const tk = auth.tokens;
  if (tk?.access) headers.Authorization = `Bearer ${tk.access}`;
  let r;
  try {
    r = await fetch(url, { method, headers, body: form || (body ? JSON.stringify(body) : undefined) });
  } catch {
    throw new ApiError(0, null);
  }
  if (r.status === 401 && retry && tk?.refresh && (await refreshAccess())) {
    return api(path, { method, body, query, form, retry: false });
  }
  if (r.status === 401 && path !== "/auth/login/") { auth.clear(); location.reload(); }
  const data = r.status === 204 ? null : await r.json().catch(() => null);
  if (!r.ok) throw new ApiError(r.status, data);
  return data;
}

export async function login(username, password) {
  const tokens = await api("/auth/login/", { method: "POST", body: { username, password }, retry: false });
  auth.save(tokens);
  const user = await api("/auth/me/");
  auth.setUser(user);
  return user;
}
