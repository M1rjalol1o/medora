// UI yordamchilari: xavfsiz HTML, toast, bottom sheet, ikonkalar, formatlash, tema.
import { t, currentLang } from "./i18n.js";

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const app = () => document.getElementById("app");

export function toast(msg, ms = 2800) {
  document.querySelector(".toast")?.remove();
  const el = document.createElement("div");
  el.className = "toast"; el.textContent = msg;
  app().appendChild(el);
  setTimeout(() => el.remove(), ms);
}

export function sheet(html, onMount) {
  closeSheet();
  const bd = document.createElement("div"); bd.className = "sheet-backdrop";
  const sh = document.createElement("div"); sh.className = "sheet";
  sh.innerHTML = `<div class="grab"></div>${html}`;
  bd.onclick = closeSheet;
  app().append(bd, sh);
  onMount?.(sh);
  return sh;
}
export function closeSheet() { document.querySelectorAll(".sheet, .sheet-backdrop").forEach((e) => e.remove()); }

const SUM = { uz: "so'm", ru: "сум", en: "UZS" };
export const som = (n) => `${Math.round(Number(n) || 0).toLocaleString("ru-RU").replace(/ |,/g, " ")} ${SUM[currentLang()] || "so'm"}`;
export const mins = (m) => (m < 60 ? t("{m} daq", { m: Math.round(m) }) : t("{h} soat {m} daq", { h: Math.floor(m / 60), m: Math.round(m % 60) }));
export const dt = (iso) => new Date(iso).toLocaleString(currentLang() === "en" ? "en-GB" : "ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

export function probLevel(p) {
  if (p >= 0.9) return { cls: "ok", color: "var(--ok)" };
  if (p >= 0.6) return { cls: "warn", color: "var(--warn)" };
  return { cls: "danger", color: "var(--danger)" };
}

export function countdown(iso) {
  const s = Math.max(0, Math.floor((new Date(iso) - Date.now()) / 1000));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  const mm = String(m).padStart(2, "0"), ss = String(sec).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

// ---- Tema: system / light / dark ----
const THEME_KEY = "apteka.theme";
export function getTheme() { try { return localStorage.getItem(THEME_KEY) || "system"; } catch { return "system"; } }
export function applyTheme(mode = getTheme()) {
  try { localStorage.setItem(THEME_KEY, mode); } catch {}
  if (mode === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", mode);
  const dark = mode === "dark" || (mode === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#0B1220" : "#0FA37F");
}

export const loc = { lat: 41.3111, lng: 69.2797, demo: true };   // joriy joylashuv (umumiy)

const P = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
export const icons = {
  search: P('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'),
  ticket: P('<path d="M3 8a2 2 0 0 0 2-2h14a2 2 0 0 0 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 0-2 2H5a2 2 0 0 0-2-2v-2a2 2 0 0 0 0-4z"/><path d="M13 6v12" stroke-dasharray="2 2"/>'),
  user: P('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'),
  users: P('<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><circle cx="17" cy="9" r="2.5"/><path d="M16 14.5a5 5 0 0 1 5.5 5"/>'),
  home: P('<path d="m3 11 9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>'),
  box: P('<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>'),
  pin: P('<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>'),
  phone: P('<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>'),
  route: P('<circle cx="6" cy="19" r="2"/><circle cx="18" cy="5" r="2"/><path d="M8 19h8a3 3 0 0 0 0-6H8a3 3 0 0 1 0-6h8"/>'),
  pill: P('<rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-45 12 12)"/><path d="m8.5 8.5 7 7"/>'),
  cart: P('<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M3 4h2l2.5 11h11L21 7H6.2"/>'),
  bag: P('<path d="M5 8h14l-1 13H6z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>'),
  heart: P('<path d="M12 20s-8-4.6-8-10.5A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 8 2.5C20 15.4 12 20 12 20z"/><path d="M8 12h2l1-2 2 4 1-2h2"/>'),
  car: P('<path d="M5 16V11l2-5h10l2 5v5"/><path d="M3 16h18v3H3z"/><circle cx="7.5" cy="16" r="1.5"/><circle cx="16.5" cy="16" r="1.5"/>'),
  wallet: P('<rect x="3" y="6" width="18" height="14" rx="2"/><path d="M3 10h18M16 15h2"/>'),
  store: P('<path d="M4 10v10h16V10M3 4h18l-1 6H4z"/><path d="M10 20v-5h4v5"/>'),
  clock: P('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
  settings: P('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>'),
  chart: P('<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>'),
};
export const ic = (name, size = 16) => icons[name].replace("<svg", `<svg style="width:${size}px;height:${size}px;vertical-align:-3px"`);
