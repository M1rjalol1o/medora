import { api, auth } from "../api.js";
import { testAlarm } from "../alarm.js";
import { changeLang } from "../app.js";
import { LANGS, currentLang, st, t } from "../i18n.js";
import { applyTheme, esc, getTheme, toast } from "../ui.js";
import { addCardFlow, cardVisual } from "./cards.js";

export function render(root, { logout }) {
  const u = auth.user || {};
  root.innerHTML = `
    <header class="topbar"><div><h1>${t("Profil")}</h1></div></header>
    <div class="screen">
      <div class="card">
        <div class="bold" style="font-size:18px">${esc(u.first_name || u.username)}</div>
        <div class="muted small mt8">${esc(st(u.role))}${u.pharmacy_name ? " · " + esc(u.pharmacy_name) : ""}${u.taxi_park_name ? " · " + esc(u.taxi_park_name) : ""}</div>
        ${u.phone ? `<div class="muted small">${esc(u.phone)}</div>` : ""}
      </div>

      <div class="section-title">${t("Til")}</div>
      <div class="seg" id="lang">${LANGS.map((l) => `<button data-v="${l.code}" class="${l.code === currentLang() ? "active" : ""}">${l.label}</button>`).join("")}</div>

      <div class="section-title">${t("Mavzu")}</div>
      <div class="seg" id="theme">
        <button data-v="light">☀️ ${t("Kunduzgi")}</button>
        <button data-v="dark">🌙 ${t("Tungi")}</button>
        <button data-v="system">⚙️ ${t("Avto")}</button>
      </div>

      ${u.role === "customer" ? `
      <div class="section-title">${t("To'lov kartalari")}</div>
      <div id="cards"><div class="spinner"></div></div>
      <button class="btn secondary" id="addCard">+ ${t("Karta qo'shish")}</button>

      <div class="section-title">${t("Dori eslatmalari")}</div>
      <div class="card small muted" style="line-height:1.5">${t("Eslatma vaqti kelganda ekran ochiladi, signal chalinadi va ovozda aytiladi. Ilova (yoki brauzer oynasi) ochiq bo'lishi kerak.")}</div>
      <div class="btn-row"><button class="btn secondary" id="notif">🔔 ${t("Bildirishnomaga ruxsat")}</button><button class="btn secondary" id="test">▶ ${t("Sinab ko'rish")}</button></div>` : ""}

      <button class="btn danger mt16" id="out">${t("Chiqish")}</button>
      <div class="tiny muted mt16" style="text-align:center">Medora v1.0 · ${t("demo ma'lumotlar")}</div>
    </div>`;

  root.querySelector("#out").onclick = logout;
  root.querySelectorAll("#lang button").forEach((b) => (b.onclick = async () => {
    changeLang(b.dataset.v);
    try { await api("/auth/me/", { method: "PATCH", body: { language: b.dataset.v } }); } catch {}
  }));
  const drawTheme = () => root.querySelectorAll("#theme button").forEach((b) => b.classList.toggle("active", b.dataset.v === getTheme()));
  root.querySelectorAll("#theme button").forEach((b) => (b.onclick = () => { applyTheme(b.dataset.v); drawTheme(); }));
  drawTheme();

  if (u.role !== "customer") return;
  const loadCards = async () => {
    const box = root.querySelector("#cards");
    try {
      const cards = await api("/payments/cards/");
      box.innerHTML = cards.map((c) => `${cardVisual(c)}<div class="row" style="margin:-4px 0 12px"><span></span><button class="btn sm danger" data-del="${c.id}">${t("O'chirish")}</button></div>`).join("")
        || `<div class="small muted" style="margin-bottom:10px">${t("Hali karta qo'shilmagan")}</div>`;
      box.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
        await api(`/payments/cards/${b.dataset.del}/`, { method: "DELETE" }); loadCards();
      }));
    } catch (e) { box.innerHTML = esc(e.message); }
  };
  root.querySelector("#addCard").onclick = async () => { await addCardFlow(); loadCards(); };
  root.querySelector("#test").onclick = () => testAlarm();
  root.querySelector("#notif").onclick = async () => {
    if (!("Notification" in window)) return toast(t("Bu qurilmada bildirishnoma yo'q"));
    const p = await Notification.requestPermission();
    toast(p === "granted" ? t("Ruxsat berildi ✓") : t("Ruxsat berilmadi"));
  };
  loadCards();
}
