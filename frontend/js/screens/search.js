// Dori qidiruvi + qolish ehtimoli bashorati + savatga qo'shish + bron
import { api } from "../api.js";
import { cart } from "../cart.js";
import { t } from "../i18n.js";
import { closeSheet, esc, ic, icons, loc, mins, probLevel, sheet, som, toast } from "../ui.js";

const state = { query: "", medicine: null, result: null, mode: "normal", travel: "car", basket: [], view: "single", basketResult: null };

const KIND = {
  recommended: ["⭐", "Tavsiya etiladi"], all_in_one: ["🏥", "Hammasi bir joyda"],
  fastest: ["⚡", "Eng tez"], safest: ["🛡", "Eng ishonchli"],
};

export function render(root, { go, params }) {
  if (params?.basket?.length) {
    state.basket = params.basket.map((b) => ({ ...b }));          // retseptdan — ro'yxat yangidan
    state.view = "basket"; state.basketResult = null;
  }
  root.innerHTML = `
    <header class="topbar"><div><h1>${t("Dori toping")}</h1>
      <div class="sub" id="loc" style="cursor:pointer">${ic("pin", 13)} <span></span></div></div>
      <div class="actions"><button class="icon-btn" id="toCart">${icons.cart}</button></div></header>
    <div class="screen">
      <div class="search-box">${icons.search}<input class="input" id="q" placeholder="${t("Dori nomi: paratsetamol, нурофен...")}" autocomplete="off" value="${esc(state.query)}"></div>
      <div id="sug"></div>
      <div id="basket"></div>
      <div class="seg mt12" id="mode">
        <button data-v="normal">⚡ ${t("Oddiy")}</button>
        <button data-v="urgent" class="urgent">🚨 ${t("Shoshilinch")}</button>
      </div>
      <div class="seg mt8" id="travel">
        <button data-v="car">🚕 ${t("Mashinada")}</button>
        <button data-v="walk">🚶 ${t("Piyoda")}</button>
      </div>
      <div id="out" class="mt16"></div>
    </div>`;

  const $ = (s) => root.querySelector(s);
  const input = $("#q");
  let timer = null;

  const drawCartBadge = () => {
    const b = $("#toCart"); b.querySelector(".badge-dot")?.remove();
    if (cart.count) b.insertAdjacentHTML("beforeend", `<span class="badge-dot">${cart.count}</span>`);
  };
  const unsub = cart.onChange(drawCartBadge);
  drawCartBadge();
  $("#toCart").onclick = () => go("cart");

  const drawLoc = () => { $("#loc span").textContent = loc.demo ? t("Toshkent markazi (demo)") : t("Joriy joylashuvingiz"); };
  $("#loc").onclick = () => {
    if (!loc.demo) { Object.assign(loc, { lat: 41.3111, lng: 69.2797, demo: true }); drawLoc(); refresh(); return; }
    if (!navigator.geolocation) return toast(t("Qurilmada GPS yo'q"));
    navigator.geolocation.getCurrentPosition(
      (p) => { Object.assign(loc, { lat: p.coords.latitude, lng: p.coords.longitude, demo: false }); drawLoc(); refresh(); },
      () => toast(t("Joylashuvga ruxsat berilmadi — demo joylashuv ishlatiladi")),
      { enableHighAccuracy: true, timeout: 8000 });
  };
  drawLoc();

  const segs = () => {
    root.querySelectorAll("#mode button").forEach((b) => b.classList.toggle("active", b.dataset.v === state.mode));
    root.querySelectorAll("#travel button").forEach((b) => b.classList.toggle("active", b.dataset.v === state.travel));
  };
  root.querySelectorAll("#mode button").forEach((b) => (b.onclick = () => { state.mode = b.dataset.v; segs(); refresh(); }));
  root.querySelectorAll("#travel button").forEach((b) => (b.onclick = () => { state.travel = b.dataset.v; segs(); refresh(); }));
  segs();

  input.oninput = () => { state.query = input.value; clearTimeout(timer); timer = setTimeout(suggest, 250); };

  async function suggest() {
    const q = state.query.trim();
    if (q.length < 2) { $("#sug").innerHTML = ""; return; }
    try {
      const meds = await api("/medicines/", { query: { q } });
      $("#sug").innerHTML = meds.length
        ? `<div class="suggest">${meds.map((m) => `<div class="row" style="border-bottom:1px solid var(--line)"><button data-id="${m.id}" style="border:0;flex:1"><b>${esc(m.name)}</b> <span class="muted small">${esc(m.dosage)} · ${esc(m.form)}${m.requires_prescription ? " · Rx" : ""}</span></button>
            <button data-add="${m.id}" title="${t("Ro'yxatga qo'shish")}" style="width:auto;border:0;padding:0 16px;font-size:22px;color:var(--primary);font-weight:700">+</button></div>`).join("")}</div>`
        : `<div class="small muted mt8" style="padding:0 4px">${t("Topilmadi. Boshqacha yozib ko'ring.")}</div>`;
      $("#sug").querySelectorAll("[data-id]").forEach((b) => (b.onclick = () => {
        const m = meds.find((x) => x.id == b.dataset.id);
        state.medicine = m; state.query = m.name; input.value = m.name; $("#sug").innerHTML = ""; input.blur();
        state.view = "single";
        refresh();
      }));
      $("#sug").querySelectorAll("[data-add]").forEach((b) => (b.onclick = () => {
        addToBasket(meds.find((x) => x.id == b.dataset.add));
        state.query = ""; input.value = ""; $("#sug").innerHTML = ""; input.focus();
      }));
    } catch (e) { toast(e.message); }
  }

  // ---------- Bir nechta dori (retsept) ----------
  function addToBasket(m) {
    if (!state.basket.some((x) => x.medicine.id === m.id)) state.basket.push({ medicine: m, quantity: 1 });
    state.basketResult = null;
    drawBasket();
    toast(t("Ro'yxatga qo'shildi: {name}", { name: m.name }));
  }

  function drawBasket() {
    const el = $("#basket");
    if (!state.basket.length) { el.innerHTML = ""; return; }
    el.innerHTML = `<div class="card mt12" style="margin-bottom:0">
      <div class="row"><b>📋 ${t("Dorilar ro'yxati")} (${state.basket.length})</b><button class="btn sm secondary" id="bclear">${t("Tozalash")}</button></div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:10px">${state.basket.map((b, i) => `
        <span class="chip ok" style="padding:6px 6px 6px 10px">${esc(b.medicine.name)} ${esc(b.medicine.dosage || "")}
          <span class="qty" style="gap:4px;margin-left:4px"><button data-bq="${i}|-1" style="width:22px;height:22px;font-size:13px">−</button><b>${b.quantity}</b><button data-bq="${i}|1" style="width:22px;height:22px;font-size:13px">+</button></span>
          <button data-brm="${i}" style="border:0;background:none;color:var(--danger);cursor:pointer;font-size:14px">✕</button></span>`).join("")}</div>
      <div class="tiny muted mt8">${t("Dori qo'shish uchun qidiruvda + tugmasini bosing")}</div>
      <button class="btn mt12" id="bsearch">🔍 ${t("Hammasini birga qidirish")}</button></div>`;
    el.querySelectorAll("[data-brm]").forEach((b) => (b.onclick = () => { state.basket.splice(Number(b.dataset.brm), 1); state.basketResult = null; drawBasket(); if (state.view === "basket") refresh(); }));
    el.querySelectorAll("[data-bq]").forEach((b) => (b.onclick = () => {
      const [i, d] = b.dataset.bq.split("|").map(Number);
      state.basket[i].quantity = Math.max(1, Math.min(20, state.basket[i].quantity + d)); state.basketResult = null; drawBasket();
    }));
    el.querySelector("#bclear").onclick = () => { state.basket = []; state.basketResult = null; state.view = "single"; drawBasket(); drawResults(); };
    el.querySelector("#bsearch").onclick = () => { state.view = "basket"; refresh(); };
  }

  async function refresh() {
    if (state.view === "basket" && state.basket.length) {
      $("#out").innerHTML = `<div class="spinner"></div>`;
      try {
        state.basketResult = await api("/basket/", { method: "POST", body: {
          items: state.basket.map((b) => ({ medicine_id: b.medicine.id, quantity: b.quantity })),
          lat: loc.lat, lng: loc.lng, mode: state.mode, travel: state.travel } });
      } catch (e) { state.basketResult = null; toast(e.message); }
      return drawBasketResult();
    }
    if (!state.medicine) return drawResults();
    $("#out").innerHTML = `<div class="spinner"></div>`;
    try {
      state.result = await api(`/medicines/${state.medicine.id}/offers/`, {
        query: { lat: loc.lat, lng: loc.lng, mode: state.mode, travel: state.travel },
      });
    } catch (e) { state.result = null; toast(e.message); }
    drawResults();
  }

  function drawBasketResult() {
    const out = $("#out");
    const r = state.basketResult;
    if (!r) { out.innerHTML = ""; return; }
    const n = r.medicines.length;
    const near = r.nearest;
    out.innerHTML = `
      ${state.mode === "urgent" ? `<div class="hint urgent">🚨 ${t("Shoshilinch: hamma dorilar yetib borguningizcha qolishi eng kafolatli variant birinchi.")}</div>` : ""}
      ${r.not_found.length ? `<div class="hint urgent mt8">❌ ${t("Hech qayerda yo'q: {list}", { list: esc(r.not_found.join(", ")) })}</div>` : ""}
      ${near ? `<div class="card mt12" style="border:1.5px dashed var(--line)">
        <div class="tiny muted">📍 ${t("Eng yaqin dorixona")} · ${mins(near.eta_minutes)}</div>
        <div class="bold mt8">${esc(near.pharmacy.name)}</div>
        <div class="small mt8">${near.covers_all ? `✅ ${t("Hammasi bor")}` : `✅ ${t("{a} / {b} ta dori bor", { a: near.has.length, b: n })} · <span style="color:var(--danger)">${t("Yo'q")}: ${esc(near.missing.join(", "))}</span>`}</div>
        ${!near.covers_all ? `<div class="tiny muted mt8">${t("Quyida — hamma dorilar bor muqobil variantlar.")}</div>` : ""}
      </div>` : ""}
      ${r.options.map(optionCard).join("") || `<div class="empty">${t("Hamma dorilarni topib bo'lmadi")}</div>`}`;
    out.querySelectorAll("[data-ocart]").forEach((b) => (b.onclick = () => {
      const o = r.options[Number(b.dataset.ocart)];
      o.stops.forEach((s) => s.items.forEach((i) => cart.add(
        { inventory_id: i.inventory_id, available: i.available, price: i.price, pharmacy: s.pharmacy },
        { name: i.name, dosage: i.dosage, requires_prescription: i.requires_prescription }, i.quantity)));
      toast(t("Hammasi savatga qo'shildi ✓"));
      go("cart");
    }));
    out.querySelectorAll("[data-ores]").forEach((b) => (b.onclick = async () => {
      const o = r.options[Number(b.dataset.ores)];
      b.disabled = true;
      let ok = 0;
      for (const s of o.stops) for (const i of s.items) {
        try { await api("/reservations/", { method: "POST", body: { inventory_id: i.inventory_id, quantity: i.quantity, lat: loc.lat, lng: loc.lng } }); ok++; }
        catch (e) { toast(`${i.name}: ${e.message}`); }
      }
      if (ok) { toast(t("{n} ta dori bron qilindi ✓", { n: ok })); go("orders", { tab: "reservations" }); }
      b.disabled = false;
    }));
  }

  function optionCard(o, idx) {
    const lv = probLevel(o.probability);
    const pct = Math.round(o.probability * 100);
    const [icon, label] = KIND[o.kind];
    const also = (o.also || []).map((k) => `<span class="chip">${KIND[k][0]} ${t(KIND[k][1])}</span>`).join(" ");
    return `<div class="card ${o.kind === "recommended" ? "recommended" : ""}">
      <div style="display:flex;flex-wrap:wrap;gap:6px"><span class="chip ${o.kind === "recommended" ? "ok" : ""}">${icon} ${t(label)}</span>${also}</div>
      <div class="row mt12"><div><div class="bold" style="font-size:18px">${mins(o.total_minutes)}</div>
        <div class="tiny muted">${o.pharmacies === 1 ? t("1 ta dorixona — hammasi bir joyda") : t("{n} ta dorixona, ketma-ket", { n: o.pharmacies })}</div></div>
        <div style="text-align:right"><div class="bold">${som(o.total_price)}</div></div></div>
      <div class="row mt12 small"><span>${t("Hammasi qolish ehtimoli")}</span><b style="color:${lv.color}">${pct}%</b></div>
      <div class="prob"><i style="width:${Math.max(pct, 3)}%;background:${lv.color}"></i></div>
      <div class="timeline mt12">${o.stops.map((s, i) => `<div class="tl-item">
        <div class="small"><b>${o.pharmacies > 1 ? i + 1 + ". " : ""}${esc(s.pharmacy.name)}</b> <span class="tiny muted">· ${mins(s.arrival_minutes)}</span></div>
        <div class="tiny muted">${esc(s.pharmacy.address)}</div>
        ${s.items.map((it) => `<div class="row tiny mt8"><span>💊 ${esc(it.name)} ${esc(it.dosage)} × ${it.quantity}</span><span><b style="color:${probLevel(it.probability).color}">${Math.round(it.probability * 100)}%</b> · ${som(it.price * it.quantity)}</span></div>`).join("")}
      </div>`).join("")}</div>
      ${!o.guaranteed ? `<div class="tiny muted">⚠ ${t("Kafolat uchun bron qiling")}</div>` : ""}
      <div class="btn-row mt12"><button class="btn sm" data-ocart="${idx}">${ic("cart", 15)} ${t("Hammasini savatga")}</button>
        <button class="btn sm secondary" data-ores="${idx}">${t("Hammasini bron qilish")}</button></div>
    </div>`;
  }

  function drawResults() {
    const out = $("#out");
    if (state.view === "basket" && state.basket.length) return drawBasketResult();
    if (!state.medicine || !state.result) {
      out.innerHTML = `<div class="empty"><div class="ic">💊</div>${t("Dori nomini yozing — qaysi dorixonada nechta borligi va yetib borguningizcha qolish ehtimolini ko'rsatamiz.")}</div>`;
      return;
    }
    const { medicine, offers } = state.result;
    const inStock = offers.filter((o) => o.available > 0);
    const hint = state.mode === "urgent"
      ? `<div class="hint urgent mt12">🚨 ${t("Shoshilinch rejim: eng yaqini emas, eng kafolatli yo'l birinchi.")}</div>`
      : `<div class="hint mt12">⚡ ${t("Oddiy rejim: o'rtacha eng tez yo'l. Shoshilinch bo'lsa yuqoridagi tugmani bosing.")}</div>`;
    out.innerHTML = `
      <div class="row"><div><div class="bold" style="font-size:18px">${esc(medicine.name)} ${esc(medicine.dosage)}</div>
        <div class="small muted">${esc(medicine.form)} · ${t("{n} ta dorixonada bor", { n: inStock.length })}</div></div>
        ${medicine.requires_prescription ? `<span class="chip warn">${t("Retsept bilan")}</span>` : ""}</div>
      <button class="btn sm secondary mt8" id="toBasket">+ ${t("Ro'yxatga qo'shish (bir nechta dori)")}</button>
      ${hint}
      <div class="mt12">${offers.map(card).join("") || `<div class="empty">${t("Hech qayerda yo'q")}</div>`}</div>`;
    out.querySelector("#toBasket").onclick = () => addToBasket(medicine);
    const find = (id) => offers.find((o) => o.inventory_id == id);
    out.querySelectorAll("[data-reserve]").forEach((b) => (b.onclick = () => openReserve(find(b.dataset.reserve))));
    out.querySelectorAll("[data-cart]").forEach((b) => (b.onclick = () => {
      cart.add(find(b.dataset.cart), medicine);
      toast(t("Savatga qo'shildi ✓"));
    }));
  }

  function card(o) {
    const lv = probLevel(o.probability);
    const pct = Math.round(o.probability * 100);
    const out = o.available === 0;
    const ph = o.pharmacy;
    const mapUrl = `https://www.google.com/maps/dir/?api=1&destination=${ph.lat},${ph.lng}`;
    return `
    <div class="card ${o.recommended ? "recommended" : ""}" style="${out ? "opacity:.55" : ""}">
      ${o.recommended ? `<div class="chip ok" style="margin-bottom:10px">★ ${t("Tavsiya etiladi")}</div>` : ""}
      <div class="row" style="align-items:flex-start">
        <div style="min-width:0">
          <div class="bold">${esc(ph.name)}</div>
          <div class="small muted" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(ph.address)}</div>
        </div>
        <div style="text-align:right;flex:none">
          ${o.discount_percent ? `<div><span class="chip disc">−${o.discount_percent}%</span> <span class="price-old">${som(o.old_price)}</span></div>` : ""}
          <div class="bold">${som(o.price)}</div>
          <div class="small" style="${o.available <= 2 && !out ? "color:var(--danger);font-weight:700" : "color:var(--muted)"}">${out ? t("Tugagan") : t("{n} dona", { n: o.available })}</div>
        </div>
      </div>
      <div class="row mt12 small">
        <span>${ic("route", 15)} ${o.distance_km} km · <b>${mins(o.eta_minutes)}</b></span>
        ${!ph.is_open ? `<span class="chip danger">${t("Yopiq")}</span>` : ph.is_24h ? '<span class="chip">24/7</span>' : ""}
      </div>
      ${out ? "" : `
      <div class="row mt12 small"><span>${t("Yetib borguningizcha qolish ehtimoli")}</span><b style="color:${lv.color}">${pct}%</b></div>
      <div class="prob"><i style="width:${Math.max(pct, 3)}%;background:${lv.color}"></i></div>
      ${!o.guaranteed ? `<div class="tiny muted mt8">⚠ ${t("Topilmasa jami ~{m} ketadi.", { m: mins(o.worst_case_minutes) })} <b>${t("Bron qilsangiz, xavf yo'q.")}</b></div>` : ""}
      <div class="btn-row mt12">
        <button class="btn sm" data-cart="${o.inventory_id}" ${!ph.is_open ? "disabled" : ""}>${ic("cart", 15)} ${t("Savatga")}</button>
        <button class="btn sm secondary" data-reserve="${o.inventory_id}" ${!ph.is_open ? "disabled" : ""}>${t("Bron")}</button>
        <a class="btn sm secondary" href="tel:${esc(ph.phone.replace(/\s|-/g, ""))}" aria-label="tel">${ic("phone", 16)}</a>
        <a class="btn sm secondary" href="${mapUrl}" target="_blank" rel="noopener" aria-label="map">${ic("route", 16)}</a>
      </div>`}
    </div>`;
  }

  function openReserve(o) {
    let qty = 1;
    const max = Math.min(o.available, 10);
    const sh = sheet(`
      <div class="bold" style="font-size:20px">${t("Bron qilish")}</div>
      <div class="muted small mt8">${esc(state.medicine.name)} ${esc(state.medicine.dosage)} · ${esc(o.pharmacy.name)}</div>
      <div class="stepper"><button id="m">−</button><span id="n">1</span><button id="p">+</button></div>
      <div class="row small"><span class="muted">${t("Jami")}</span><b id="sum">${som(o.price)}</b></div>
      <div class="hint mt12">${t("Dori siz uchun {m} saqlab turiladi: piyoda yo'l vaqtingiz + 20 daqiqa. To'lov dorixonada.", { m: `<b>${mins(o.hold_minutes)}</b>` })}</div>
      ${state.medicine.requires_prescription ? `<div class="hint urgent mt8">${t("Retseptli dori: dorixonaga retseptni olib boring.")}</div>` : ""}
      <button class="btn mt16" id="ok">${t("Tasdiqlash")}</button>`);
    const upd = () => { sh.querySelector("#n").textContent = qty; sh.querySelector("#sum").textContent = som(o.price * qty); };
    sh.querySelector("#m").onclick = () => { qty = Math.max(1, qty - 1); upd(); };
    sh.querySelector("#p").onclick = () => { qty = Math.min(max, qty + 1); upd(); };
    sh.querySelector("#ok").onclick = async (e) => {
      e.target.disabled = true;
      try {
        const r = await api("/reservations/", { method: "POST", body: { inventory_id: o.inventory_id, quantity: qty, lat: loc.lat, lng: loc.lng } });
        closeSheet();
        sheet(`
          <div style="text-align:center"><div style="font-size:44px">✅</div>
          <div class="bold" style="font-size:20px">${t("Bron qilindi!")}</div>
          <div class="muted small mt8">${esc(r.pharmacy.name)} — ${esc(r.pharmacy.address)}</div>
          <div class="muted small mt16">${t("Dorixonada shu kodni ayting:")}</div>
          <div class="code-big">${esc(r.code)}</div>
          <div class="small muted">${t("{m} ichida olib keting", { m: mins(r.hold_minutes) })}</div></div>
          <button class="btn mt16" id="see">${t("Bronlarimga o'tish")}</button>`, (s) => {
          s.querySelector("#see").onclick = () => { closeSheet(); go("orders", { tab: "reservations" }); };
        });
        refresh();
      } catch (err) { toast(err.message); e.target.disabled = false; }
    };
  }

  drawBasket();
  if (state.view === "basket" && state.basket.length && !state.basketResult) refresh(); else drawResults();
  return () => { clearTimeout(timer); unsub(); };
}
