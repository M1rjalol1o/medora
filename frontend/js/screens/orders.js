// Mijoz: buyurtmalar (kuzatish xaritada) va bronlar
import { api } from "../api.js";
import { drawRouteMap } from "../map.js";
import { st, t } from "../i18n.js";
import { closeSheet, countdown, dt, esc, ic, mins, sheet, som, toast } from "../ui.js";

const state = { tab: "orders", openId: null };

export function render(root, { go, params }) {
  if (params?.tab) state.tab = params.tab;
  if (params?.order) { state.tab = "orders"; state.openId = params.order; }
  root.innerHTML = `<header class="topbar"><div><h1>${t("Buyurtmalar")}</h1></div></header>
    <div class="screen"><div class="seg" id="seg"><button data-v="orders">${t("Buyurtmalar")}</button><button data-v="reservations">${t("Bronlar")}</button></div>
    <div id="c" class="mt12"><div class="spinner"></div></div></div>`;
  const c = root.querySelector("#c");
  let mapCtl = null, lastKey = "";

  root.querySelectorAll("#seg button").forEach((b) => (b.onclick = () => { state.tab = b.dataset.v; state.openId = null; segs(); load(true); }));
  const segs = () => root.querySelectorAll("#seg button").forEach((b) => b.classList.toggle("active", b.dataset.v === state.tab));
  segs();

  async function load(force) {
    try {
      if (state.tab === "reservations") return drawReservations(await api("/reservations/"));
      if (state.openId) return drawDetail(await api(`/orders/${state.openId}/`), force);
      drawList(await api("/orders/"));
    } catch (e) { c.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }

  // ---------- Ro'yxat ----------
  function drawList(orders) {
    mapCtl = null;
    if (!orders.length) {
      c.innerHTML = `<div class="empty"><div class="ic">📦</div>${t("Hali buyurtma yo'q")}<br><button class="btn mt16" id="find">${t("Dori qidirish")}</button></div>`;
      c.querySelector("#find").onclick = () => go("search");
      return;
    }
    c.innerHTML = orders.map((o) => `
      <div class="card" data-open="${o.id}" style="cursor:pointer">
        <div class="row"><b>#${o.id} · ${som(o.total)}</b><span class="chip ${chipCls(o.status)}">${esc(st(o.status))}</span></div>
        <div class="small muted mt8">${o.pharmacy_orders.map((p) => esc(p.pharmacy.name)).join(" · ")}</div>
        <div class="tiny muted mt8">${dt(o.created_at)} · ${esc(st(o.fulfillment))} · ${esc(st(o.payment_method))}</div>
      </div>`).join("");
    c.querySelectorAll("[data-open]").forEach((el) => (el.onclick = () => { state.openId = Number(el.dataset.open); load(true); }));
  }

  const chipCls = (s) => (["completed", "delivered"].includes(s) ? "ok" : s === "cancelled" ? "danger" : "warn");

  // ---------- Batafsil + kuzatish ----------
  function steps(o) {
    const d = o.delivery;
    if (o.fulfillment === "pickup") {
      const order = ["confirmed", "preparing", "ready", "completed"];
      const idx = order.indexOf(o.status);
      return [["Qabul qilindi", 0], ["Tayyorlanmoqda", 1], ["Olib ketishga tayyor", 2], ["Yakunlandi", 3]].map(([l, i]) => [l, i < idx ? "done" : i === idx ? "current" : ""]);
    }
    const ds = d?.status || "searching";
    const level = o.status === "completed" ? 5 : ds === "delivering" ? 4 : ds === "picking" ? 3 : ds === "assigned" ? 2 : ["preparing", "ready"].includes(o.status) ? 1 : 0;
    return [["Qabul qilindi"], ["Dorixonalar tayyorlamoqda"], ["Haydovchi biriktirildi"], ["Dorixonalardan olinmoqda"], ["Yo'lda"], ["Yetkazildi"]]
      .map(([l], i) => [l, i < level ? "done" : i === level ? (level === 5 ? "done" : "current") : ""]);
  }

  async function drawDetail(o, force) {
    const key = JSON.stringify([o.status, o.delivery?.status, o.delivery?.driver?.lat, o.delivery?.driver?.lng, o.pharmacy_orders.map((p) => p.status), o.is_paid]);
    if (!force && key === lastKey) return;
    lastKey = key;
    const d = o.delivery;
    const canCancel = !["completed", "cancelled", "delivering"].includes(o.status) && (!d || ["searching", "assigned"].includes(d.status))
      && !o.pharmacy_orders.some((p) => ["picked_up", "issued"].includes(p.status));
    c.innerHTML = `
      <button class="btn secondary sm" id="back">← ${t("Orqaga")}</button>
      <div class="row mt12"><div class="bold" style="font-size:20px">#${o.id}</div><span class="chip ${chipCls(o.status)}">${esc(st(o.status))}</span></div>

      ${o.status === "awaiting_payment" ? `<div class="hint urgent mt12">${t("To'lov amalga oshmadi. Qayta urinib ko'ring — 15 daqiqadan keyin buyurtma bekor bo'ladi.")}</div>
        <button class="btn mt8" id="pay">${t("To'lash · {s}", { s: som(o.total) })}</button>` : ""}

      ${o.fulfillment === "delivery" && d ? `
        ${o.status !== "cancelled" ? `<div class="map mt12" id="map"></div>` : ""}
        ${d.driver ? `<div class="card"><div class="row"><div><div class="bold">🚕 ${esc(d.driver.name)}</div>
            <div class="small muted">${esc(d.driver.car_model)} · <b>${esc(d.driver.car_number)}</b> · ${esc(d.driver.park)}</div></div>
            <a class="btn sm secondary" href="tel:${esc((d.driver.phone || "").replace(/\s|-/g, ""))}">${ic("phone", 16)}</a></div></div>`
          : o.status !== "cancelled" ? `<div class="card small muted">⏳ ${t("Haydovchi qidirilmoqda...")}</div>` : ""}
        ${!["completed", "cancelled"].includes(o.status) ? `<div class="card" style="text-align:center"><div class="small muted">${t("Haydovchiga shu kodni ayting (dorini olganingizda):")}</div>
          <div class="code-big">${esc(o.delivery_code)}</div>
          ${o.payment_method === "cash" ? `<div class="small">💵 ${t("Haydovchiga naqd: {s}", { s: `<b>${som(o.total)}</b>` })}</div>` : ""}</div>` : ""}` : ""}

      <div class="card"><div class="timeline">${steps(o).map(([l, cls]) => `<div class="tl-item ${cls}"><div class="small ${cls ? "bold" : "muted"}">${esc(t(l))}</div></div>`).join("")}</div></div>

      ${o.pharmacy_orders.map((p) => `
        <div class="card">
          <div class="row"><div class="bold">${ic("store", 15)} ${esc(p.pharmacy.name)}</div><span class="chip ${p.status === "rejected" ? "danger" : ["ready", "picked_up", "issued"].includes(p.status) ? "ok" : ""}">${esc(st(p.status))}</span></div>
          <div class="tiny muted">${esc(p.pharmacy.address)}</div>
          ${p.items.map((i) => `<div class="row small mt8"><span>${esc(i.medicine_name)} × ${i.quantity}</span><span>${som(i.price * i.quantity)}</span></div>`).join("")}
          ${o.fulfillment === "pickup" && !["issued", "rejected"].includes(p.status) && o.status !== "cancelled" ? `<div class="mt12" style="text-align:center"><div class="tiny muted">${t("Dorixonada shu kodni ayting:")}</div><div class="code-big" style="font-size:30px">${esc(p.pickup_code)}</div></div>` : ""}
        </div>`).join("")}

      <div class="card">
        <div class="row small"><span class="muted">${t("Dorilar")}</span><span>${som(o.items_total)}</span></div>
        ${o.delivery_fee ? `<div class="row small mt8"><span class="muted">${t("Yetkazish")}</span><span>${som(o.delivery_fee)}</span></div>` : ""}
        <div class="row mt12"><b>${t("Jami")}</b><b>${som(o.total)}</b></div>
        <div class="row tiny muted mt8"><span>${esc(st(o.payment_method))}</span><span>${esc(st(o.payment_status || ""))}</span></div>
      </div>
      ${canCancel ? `<button class="btn danger" id="cancel">${t("Buyurtmani bekor qilish")}</button>` : ""}`;

    c.querySelector("#back").onclick = () => { state.openId = null; lastKey = ""; load(true); };
    c.querySelector("#cancel")?.addEventListener("click", async () => {
      try { await api(`/orders/${o.id}/cancel/`, { method: "POST" }); toast(t("Bekor qilindi. Pul kartaga qaytariladi.")); load(true); }
      catch (e) { toast(e.message); }
    });
    c.querySelector("#pay")?.addEventListener("click", () => payFlow(o));
    const mapEl = c.querySelector("#map");
    if (mapEl && d) {
      const pts = d.stops.map((s, i) => ({ lat: s.lat, lng: s.lng, label: s.kind === "dropoff" ? "🏠" : String(i + 1), color: s.done_at ? "#9CA3AF" : s.kind === "dropoff" ? "#E5484D" : "#0FA37F" }));
      mapCtl = await drawRouteMap(mapEl, pts, d.driver);
    }
  }

  async function payFlow(o) {
    const cards = await api("/payments/cards/");
    const sh = sheet(`<div class="bold" style="font-size:20px">${t("Karta tanlang")}</div><div class="mt12">
      ${cards.map((k) => `<button class="radio-card" style="width:100%" data-card="${k.id}"><b>${esc(k.brand)}</b>&nbsp;${esc(k.masked)}</button>`).join("") || `<div class="muted small">${t("Profil bo'limida karta qo'shing")}</div>`}</div>`);
    sh.querySelectorAll("[data-card]").forEach((b) => (b.onclick = async () => {
      try { await api(`/payments/orders/${o.id}/pay/`, { method: "POST", body: { card_id: Number(b.dataset.card) } }); closeSheet(); toast(t("To'landi ✓")); load(true); }
      catch (e) { toast(e.message); }
    }));
  }

  // ---------- Bronlar ----------
  function drawReservations(items) {
    if (!items.length) {
      c.innerHTML = `<div class="empty"><div class="ic">🎫</div>${t("Hali bron yo'q.")}<br><button class="btn mt16" id="find">${t("Dori qidirish")}</button></div>`;
      c.querySelector("#find").onclick = () => go("search");
      return;
    }
    const active = items.filter((r) => ["pending", "confirmed"].includes(r.status));
    const past = items.filter((r) => !["pending", "confirmed"].includes(r.status));
    c.innerHTML = `
      ${active.map((r) => `
        <div class="card recommended">
          <div class="row"><span class="chip ${r.status === "confirmed" ? "ok" : "warn"}">${esc(st(r.status))}</span><b data-cd="${esc(r.expires_at)}">${countdown(r.expires_at)}</b></div>
          <div class="bold mt12" style="font-size:17px">${esc(r.medicine.name)} ${esc(r.medicine.dosage)} × ${r.quantity}</div>
          <div class="small muted">${esc(r.pharmacy.name)} · ${esc(r.pharmacy.address)}</div>
          <div class="tiny muted mt8">${t("Saqlash muddati: {m} (piyoda yo'l + 20 daqiqa)", { m: mins(r.hold_minutes) })}</div>
          <div class="muted small mt12" style="text-align:center">${t("Dorixonada shu kodni ayting:")}</div>
          <div class="code-big">${esc(r.code)}</div>
          <div class="btn-row">
            <a class="btn sm secondary" target="_blank" rel="noopener" href="https://www.google.com/maps/dir/?api=1&destination=${r.pharmacy.lat},${r.pharmacy.lng}&travelmode=walking">${t("Yo'l ko'rsatish")}</a>
            <button class="btn sm danger" data-cancel="${r.id}">${t("Bekor qilish")}</button>
          </div>
        </div>`).join("")}
      ${past.length ? `<div class="section-title">${t("Tarix")}</div>${past.map((r) => `
        <div class="card"><div class="row"><div><div class="bold">${esc(r.medicine.name)} × ${r.quantity}</div>
        <div class="tiny muted">${esc(r.pharmacy.name)} · ${dt(r.created_at)}</div></div>
        <span class="chip ${r.status === "completed" ? "ok" : ""}">${esc(st(r.status))}</span></div></div>`).join("")}` : ""}`;
    c.querySelectorAll("[data-cancel]").forEach((b) => (b.onclick = async () => {
      try { await api(`/reservations/${b.dataset.cancel}/cancel/`, { method: "POST" }); toast(t("Bron bekor qilindi")); load(true); }
      catch (e) { toast(e.message); }
    }));
  }

  const tick = setInterval(() => c.querySelectorAll("[data-cd]").forEach((el) => (el.textContent = countdown(el.dataset.cd))), 1000);
  const poll = setInterval(() => load(false), 8000);
  load(true);
  return () => { clearInterval(tick); clearInterval(poll); };
}
