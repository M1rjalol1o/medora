// Taksopark paneli: haydovchilar, yetkazishlar, dispetcherlik, daromad
import { api, auth } from "../api.js";
import { st, t } from "../i18n.js";
import { closeSheet, dt, esc, sheet, som, toast } from "../ui.js";

const header = (title) => `<header class="topbar"><div><h1>${t(title)}</h1><div class="sub">${esc(auth.user?.taxi_park_name || "")}</div></div></header>`;

export const dashboard = {
  render(root, { go }) {
    root.innerHTML = `${header("Bosh sahifa")}<div class="screen" id="c"><div class="spinner"></div></div>`;
    const c = root.querySelector("#c");
    async function load() {
      try {
        const d = await api("/park/dashboard/");
        c.innerHTML = `
          <div class="stat-grid">
            <div class="stat"><div class="v" style="color:var(--primary)">${d.drivers_online}/${d.drivers_total}</div><div class="k">${t("Onlayn haydovchilar")}</div></div>
            <div class="stat"><div class="v">${d.active_deliveries}</div><div class="k">${t("Faol yetkazishlar")}</div></div>
            <div class="stat"><div class="v">${d.today_deliveries}</div><div class="k">${t("Bugun yetkazildi")}</div></div>
            <div class="stat"><div class="v" style="color:var(--warn)">${d.waiting_in_city}</div><div class="k">${t("Shaharda kutilmoqda")}</div></div>
            <div class="stat"><div class="v">${som(d.today_turnover)}</div><div class="k">${t("Bugungi aylanma")}</div></div>
            <div class="stat"><div class="v" style="color:var(--primary)">${som(d.today_park_earning)}</div><div class="k">${t("Park ulushi ({p}%)", { p: d.park.commission_percent })}</div></div>
          </div>
          ${d.waiting_in_city ? `<button class="btn" id="dispatch">${t("Kutilayotgan buyurtmalarni taqsimlash")}</button>` : ""}`;
        c.querySelector("#dispatch")?.addEventListener("click", () => go("deliveries"));
      } catch (e) { c.innerHTML = esc(e.message); }
    }
    load();
    const tm = setInterval(load, 15000);
    return () => clearInterval(tm);
  },
};

export const drivers = {
  render(root) {
    root.innerHTML = `${header("Haydovchilar")}<div class="screen" id="c"><div class="spinner"></div></div>`;
    const c = root.querySelector("#c");
    async function load() {
      try {
        const rows = await api("/park/drivers/");
        c.innerHTML = rows.map((d) => `
          <div class="card"><div class="row"><div><div class="bold">${d.is_online ? "🟢" : "⚪"} ${esc(d.name)}</div>
            <div class="small muted">${esc(d.car_model)} · <b>${esc(d.car_number)}</b> · ★ ${d.rating.toFixed(1)}</div>
            <div class="tiny muted">${esc(d.phone || "")}</div></div>
            <div style="text-align:right">${d.busy ? `<span class="chip warn">${t("Band")} #${d.active_order}</span>` : d.is_online ? `<span class="chip ok">${t("Bo'sh")}</span>` : `<span class="chip">${t("Oflayn")}</span>`}
            <div class="tiny muted mt8">${t("bugun")}: ${d.today_done} · ${som(d.today_earning)}</div></div></div></div>`).join("") || `<div class="empty">${t("Haydovchi yo'q")}</div>`;
      } catch (e) { c.innerHTML = esc(e.message); }
    }
    load();
    const tm = setInterval(load, 15000);
    return () => clearInterval(tm);
  },
};

export const deliveries = {
  render(root) {
    root.innerHTML = `${header("Yetkazishlar")}<div class="screen" id="c"><div class="spinner"></div></div>`;
    const c = root.querySelector("#c");
    async function load() {
      try {
        const d = await api("/park/deliveries/");
        const row = (x, assign) => `
          <div class="card ${assign ? "recommended" : ""}">
            <div class="row"><b>#${x.order_id} · ${som(x.fee)}</b><span class="chip ${x.status === "delivered" ? "ok" : "warn"}">${esc(st(x.status))}</span></div>
            <div class="small muted mt8">${x.stops.map((s) => (s.kind === "pickup" ? "🏥 " : "🏠 ") + esc(s.title)).join(" → ")}</div>
            <div class="tiny muted mt8">${x.distance_km} km · ${esc(st(x.payment_method))} · ${dt(x.created_at)}${x.driver ? " · 🚕 " + esc(x.driver.name) : ""}</div>
            ${assign ? `<button class="btn sm mt12" data-assign="${x.id}">${t("Haydovchiga biriktirish")}</button>` : ""}
          </div>`;
        c.innerHTML = `<div class="section-title">${t("Haydovchi kutayotganlar")} (${d.waiting.length})</div>
          ${d.waiting.map((x) => row(x, true)).join("") || `<div class="small muted">${t("Yo'q")}</div>`}
          <div class="section-title">${t("Parkimiz yetkazishlari")}</div>${d.mine.map((x) => row(x, false)).join("") || `<div class="small muted">${t("Yo'q")}</div>`}`;
        c.querySelectorAll("[data-assign]").forEach((b) => (b.onclick = () => assign(b.dataset.assign)));
      } catch (e) { c.innerHTML = esc(e.message); }
    }
    async function assign(id) {
      const ds = (await api("/park/drivers/")).filter((d) => d.is_online && !d.busy);
      const sh = sheet(`<div class="bold" style="font-size:20px">${t("Bo'sh haydovchini tanlang")}</div><div class="mt12">
        ${ds.map((d) => `<button class="radio-card" style="width:100%" data-d="${d.id}"><b>${esc(d.name)}</b>&nbsp;· ${esc(d.car_number)}</button>`).join("") || `<div class="muted small">${t("Bo'sh onlayn haydovchi yo'q")}</div>`}</div>`);
      sh.querySelectorAll("[data-d]").forEach((b) => (b.onclick = async () => {
        try { await api(`/park/deliveries/${id}/assign/`, { method: "POST", body: { driver_id: Number(b.dataset.d) } }); closeSheet(); toast(t("Biriktirildi ✓")); load(); }
        catch (e) { toast(e.message); }
      }));
    }
    load();
    const tm = setInterval(() => { if (!document.querySelector(".sheet")) load(); }, 12000);
    return () => clearInterval(tm);
  },
};
