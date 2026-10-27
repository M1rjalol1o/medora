// Haydovchi ilovasi: onlayn/oflayn, topshiriqlar, marshrut (bir nechta dorixona -> mijoz), daromad
import { api } from "../api.js";
import { drawRouteMap } from "../map.js";
import { st, t } from "../i18n.js";
import { closeSheet, dt, esc, ic, sheet, som, toast } from "../ui.js";

const navUrl = (s) => `https://www.google.com/maps/dir/?api=1&destination=${s.lat},${s.lng}`;

export const tasks = {
  render(root) {
    root.innerHTML = `<header class="topbar"><div><h1>${t("Topshiriqlar")}</h1><div class="sub" id="sub"></div></div>
      <div class="actions"><button class="btn sm" id="online"></button></div></header>
      <div class="screen" id="c"><div class="spinner"></div></div>`;
    const c = root.querySelector("#c");
    let me = null, current = null, lastKey = "", watchId = null, lastSent = 0;

    async function sendLoc(lat, lng) {
      try { await api("/driver/location/", { method: "POST", body: { lat, lng } }); } catch {}
    }
    if (navigator.geolocation) {
      watchId = navigator.geolocation.watchPosition((p) => {
        if (Date.now() - lastSent > 15000) { lastSent = Date.now(); sendLoc(p.coords.latitude, p.coords.longitude); }
      }, () => {}, { enableHighAccuracy: true });
    }

    async function load(force) {
      try {
        [me, current] = await Promise.all([api("/driver/me/"), api("/driver/current/")]);
      } catch (e) { c.innerHTML = esc(e.message); return; }
      const ob = root.querySelector("#online");
      ob.textContent = me.is_online ? "🟢 " + t("Onlayn") : "⚪ " + t("Oflayn");
      ob.className = "btn sm " + (me.is_online ? "" : "secondary");
      root.querySelector("#sub").textContent = `${me.driver.car_model} · ${me.driver.car_number} · ${t("bugun")}: ${som(me.today_earning)}`;
      if (current) return drawCurrent(current, force);
      lastKey = "";
      if (!me.is_online) {
        c.innerHTML = `<div class="empty"><div class="ic">😴</div>${t("Siz oflaynsiz. Buyurtma olish uchun 'Onlayn' tugmasini bosing.")}</div>`;
        return;
      }
      const list = await api("/driver/available/");
      c.innerHTML = `<div class="section-title">${t("Yaqin atrofdagi buyurtmalar")} (${list.length})</div>` + (list.map((d) => `
        <div class="card">
          <div class="row"><b>${som(d.fee)}</b><span class="chip">${d.distance_km} km · ${t("{n} ta dorixona", { n: d.stops.length - 1 })}</span></div>
          ${d.to_first_stop_km !== undefined ? `<div class="tiny muted mt8">${t("Birinchi dorixonagacha {km} km", { km: d.to_first_stop_km })}</div>` : ""}
          <div class="timeline mt12">${d.stops.map((s) => `<div class="tl-item"><div class="small"><b>${s.kind === "pickup" ? "🏥" : "🏠"} ${esc(s.title)}</b></div><div class="tiny muted">${esc(s.address)}</div></div>`).join("")}</div>
          ${d.collect_cash ? `<div class="hint urgent small">💵 ${t("Mijozdan naqd olinadi: {s}", { s: `<b>${som(d.collect_cash)}</b>` })}</div>` : `<div class="hint small">💳 ${t("Mijoz ilovada to'lagan")}</div>`}
          <button class="btn mt12" data-accept="${d.id}">${t("Qabul qilish")}</button>
        </div>`).join("") || `<div class="empty"><div class="ic">📡</div>${t("Hozircha buyurtma yo'q. Yangi buyurtma kelsa shu yerda chiqadi.")}</div>`);
      c.querySelectorAll("[data-accept]").forEach((b) => (b.onclick = async () => {
        try { await api(`/driver/deliveries/${b.dataset.accept}/accept/`, { method: "POST" }); toast(t("Buyurtma sizniki! Birinchi dorixonaga boring.")); load(true); }
        catch (e) { toast(e.message); load(true); }
      }));
    }

    async function drawCurrent(d, force) {
      const key = JSON.stringify([d.status, d.stops.map((s) => s.done_at), d.pharmacy_orders.map((p) => p.status)]);
      if (!force && key === lastKey) return;
      lastKey = key;
      const next = d.stops.find((s) => !s.done_at);
      const poStatus = (s) => d.pharmacy_orders.find((p) => p.id === s.pharmacy_order_id);
      c.innerHTML = `
        <div class="map" id="map"></div>
        <div class="card"><div class="row"><div><div class="bold">#${d.order_id} · ${esc(st(d.status))}</div>
          <div class="small muted">${esc(d.customer.name)} · ${esc(d.customer.phone || "")}</div></div>
          <div style="text-align:right"><div class="bold">${som(d.fee)}</div><div class="tiny muted">${d.distance_km} km</div></div></div>
          ${d.collect_cash ? `<div class="hint urgent small mt8">💵 ${t("Mijozdan naqd oling: {s}", { s: `<b>${som(d.collect_cash)}</b>` })}</div>` : ""}</div>
        ${d.stops.map((s, i) => {
          const po = poStatus(s);
          const isNext = next && s.id === next.id;
          return `<div class="card ${isNext ? "recommended" : ""}" style="${s.done_at ? "opacity:.55" : ""}">
            <div class="row"><div><div class="bold">${s.kind === "pickup" ? `🏥 ${i + 1}. ` : "🏠 "}${esc(s.title)}</div><div class="tiny muted">${esc(s.address)}</div></div>
              ${s.done_at ? `<span class="chip ok">✓</span>` : po ? `<span class="chip ${po.status === "ready" ? "ok" : "warn"}">${esc(st(po.status))}</span>` : ""}</div>
            ${po ? `<div class="tiny muted mt8">${po.items.map(esc).join(" · ")}</div>` : ""}
            ${isNext ? `<div class="btn-row mt12">
              <a class="btn sm secondary" href="${navUrl(s)}" target="_blank" rel="noopener">${ic("route", 15)} ${t("Navigator")}</a>
              <button class="btn sm secondary" data-here="${s.id}">📍 ${t("Yetib keldim")}</button>
              <button class="btn sm" data-done="${s.id}" data-kind="${s.kind}">${s.kind === "pickup" ? t("Oldim") : t("Topshirdim")}</button></div>` : ""}
          </div>`;
        }).join("")}`;
      c.querySelectorAll("[data-here]").forEach((b) => (b.onclick = () => {
        const s = d.stops.find((x) => x.id == b.dataset.here); sendLoc(s.lat, s.lng); toast(t("Joylashuv yangilandi"));
      }));
      c.querySelectorAll("[data-done]").forEach((b) => (b.onclick = () => {
        if (b.dataset.kind === "pickup") return done(b.dataset.done, {});
        const sh = sheet(`<div class="bold" style="font-size:20px">${t("Mijozga topshirish")}</div>
          <div class="small muted mt8">${t("Mijoz ilovasidagi 4 xonali kodni so'rang")}</div>
          ${d.collect_cash ? `<div class="hint urgent mt12">💵 ${t("Avval naqd pulni oling: {s}", { s: `<b>${som(d.collect_cash)}</b>` })}</div>` : ""}
          <input class="input mt16" id="code" inputmode="numeric" maxlength="4" style="font-size:28px;text-align:center;letter-spacing:10px">
          <button class="btn mt16" id="ok">${t("Tasdiqlash")}</button>`);
        sh.querySelector("#ok").onclick = () => done(b.dataset.done, { code: sh.querySelector("#code").value });
      }));
      const pts = d.stops.map((s, i) => ({ lat: s.lat, lng: s.lng, label: s.kind === "dropoff" ? "🏠" : String(i + 1), color: s.done_at ? "#9CA3AF" : s.kind === "dropoff" ? "#E5484D" : "#0FA37F" }));
      drawRouteMap(c.querySelector("#map"), pts, me.driver);
    }

    async function done(id, body) {
      try {
        const r = await api(`/driver/stops/${id}/done/`, { method: "POST", body });
        closeSheet();
        if (r.status === "delivered") toast(t("Yetkazildi! Daromad: {s}", { s: som(r.driver_earning) }), 4000);
        load(true);
      } catch (e) { toast(e.message); }
    }

    root.querySelector("#online").onclick = async () => {
      try { await api("/driver/online/", { method: "POST", body: { is_online: !me.is_online } }); load(true); } catch (e) { toast(e.message); }
    };
    load(true);
    const poll = setInterval(() => { if (!document.querySelector(".sheet")) load(false); }, 8000);
    return () => { clearInterval(poll); if (watchId !== null) navigator.geolocation.clearWatch(watchId); };
  },
};

export const earnings = {
  render(root) {
    root.innerHTML = `<header class="topbar"><div><h1>${t("Daromad")}</h1></div></header><div class="screen" id="c"><div class="spinner"></div></div>`;
    const c = root.querySelector("#c");
    (async () => {
      try {
        const [me, hist] = await Promise.all([api("/driver/me/"), api("/driver/history/")]);
        c.innerHTML = `
          <div class="stat-grid">
            <div class="stat"><div class="v" style="color:var(--primary)">${som(me.today_earning)}</div><div class="k">${t("Bugungi daromad")}</div></div>
            <div class="stat"><div class="v">${me.today_count}</div><div class="k">${t("Bugun yetkazildi")}</div></div>
            <div class="stat"><div class="v">${som(me.cash_on_hand)}</div><div class="k">${t("Qo'ldagi naqd (bugun)")}</div></div>
            <div class="stat"><div class="v">${som(me.total_earning)}</div><div class="k">${t("Jami daromad")}</div></div>
          </div>
          <div class="hint small">${t("Naqd pulning dorilar qismi taksopark orqali dorixonalarga hisob-kitob qilinadi.")}</div>
          <div class="section-title">${t("Tarix")}</div>
          ${hist.map((d) => `<div class="card"><div class="row"><div><b>#${d.order_id}</b> <span class="small muted">${d.distance_km} km</span>
            <div class="tiny muted">${dt(d.created_at)} · ${esc(st(d.payment_method))}</div></div>
            <div style="text-align:right"><b style="color:var(--primary)">+${som(d.driver_earning)}</b><div class="tiny muted">${t("narx")} ${som(d.fee)}</div></div></div></div>`).join("")
            || `<div class="empty">${t("Hali yetkazish yo'q")}</div>`}`;
      } catch (e) { c.innerHTML = esc(e.message); }
    })();
  },
};
