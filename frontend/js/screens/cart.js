// Savat va rasmiylashtirish: bir nechta dorixona + taksi = BITTA to'lov
import { api } from "../api.js";
import { cart } from "../cart.js";
import { t } from "../i18n.js";
import { esc, ic, loc, som, toast } from "../ui.js";
import { addCardFlow } from "./cards.js";

const state = { fulfillment: "delivery", method: "card", cardId: null, address: "", rxId: null, comment: "" };

export function render(root, { go }) {
  root.innerHTML = `<header class="topbar"><div><h1>${t("Savat")}</h1><div class="sub">${t("Bir nechta dorixona — bitta to'lov")}</div></div></header>
    <div class="screen" id="c"></div>`;
  const c = root.querySelector("#c");
  let cards = [], rxList = [], quote = null, qTimer = null;

  async function loadSide() {
    try { [cards, rxList] = await Promise.all([api("/payments/cards/"), api("/prescriptions/")]); } catch {}
    if (!state.cardId && cards[0]) state.cardId = cards[0].id;
    draw();
  }

  async function requote() {
    const items = cart.items.map((i) => ({ inventory_id: i.inventory_id, quantity: i.quantity }));
    if (!items.length) { quote = null; return draw(); }
    try {
      quote = await api("/orders/quote/", { method: "POST", body: { items, fulfillment: state.fulfillment, lat: loc.lat, lng: loc.lng } });
    } catch (e) { toast(e.message); }
    drawTotals();
  }

  function draw() {
    const items = cart.items;
    if (!items.length) {
      c.innerHTML = `<div class="empty"><div class="ic">🛒</div>${t("Savat bo'sh")}<br><button class="btn mt16" id="find">${t("Dori qidirish")}</button></div>`;
      c.querySelector("#find").onclick = () => go("search");
      return;
    }
    const groups = {};
    items.forEach((i) => (groups[i.pharmacy_id] ||= { name: i.pharmacy, items: [] }).items.push(i));

    c.innerHTML = `
      ${Object.values(groups).map((g) => `
        <div class="card">
          <div class="bold">${ic("store", 15)} ${esc(g.name)}</div>
          ${g.items.map((i) => `
            <div class="list-row">
              <div style="min-width:0"><div class="bold small">${esc(i.name)} ${esc(i.dosage)} ${i.rx ? '<span class="chip warn">Rx</span>' : ""}</div>
                <div class="tiny muted">${som(i.price)}</div></div>
              <div class="qty"><button data-dec="${i.inventory_id}">−</button><b>${i.quantity}</b><button data-inc="${i.inventory_id}">+</button></div>
            </div>`).join("")}
        </div>`).join("")}

      <div class="section-title">${t("Qanday olasiz?")}</div>
      <div class="seg" id="ful">
        <button data-v="delivery">🚕 ${t("Yetkazib berish")}</button>
        <button data-v="pickup">🏥 ${t("O'zim olib ketaman")}</button>
      </div>
      ${state.fulfillment === "delivery" ? `
        <label class="lbl">${t("Manzil")}</label>
        <input class="input" id="addr" placeholder="${t("Ko'cha, uy, xonadon, mo'ljal")}" value="${esc(state.address)}">
        <div class="tiny muted mt8">${ic("pin", 12)} ${loc.demo ? t("Toshkent markazi (demo)") : t("Joriy joylashuvingiz")} — ${t("haydovchi shu nuqtaga keladi")}</div>` : ""}

      ${cart.hasRx ? `
        <div class="section-title">${t("Retsept")}</div>
        <div class="hint urgent">${t("Savatda retseptli dori bor. Retseptni biriktiring — farmatsevt tekshiradi.")}</div>
        ${rxList.length ? rxList.map((r) => `<label class="radio-card ${state.rxId === r.id ? "active" : ""}"><input type="radio" name="rx" value="${r.id}" ${state.rxId === r.id ? "checked" : ""}>
          <div><div class="bold small">${t("Retsept")} #${r.id}</div><div class="tiny muted">${esc((r.items.map((x) => x.name).join(", ") || r.raw_text).slice(0, 60))}</div></div></label>`).join("") : ""}
        <button class="btn secondary sm" id="newRx">+ ${t("Retsept yuklash")}</button>` : ""}

      <div class="section-title">${t("To'lov")}</div>
      <label class="radio-card ${state.method === "card" ? "active" : ""}"><input type="radio" name="pm" value="card" ${state.method === "card" ? "checked" : ""}>
        <div><div class="bold">💳 ${t("Karta orqali — ilovada")}</div><div class="tiny muted">${t("Dorilar va taksi uchun bitta to'lov")}</div></div></label>
      <label class="radio-card ${state.method === "cash" ? "active" : ""}"><input type="radio" name="pm" value="cash" ${state.method === "cash" ? "checked" : ""}>
        <div><div class="bold">💵 ${t("Naqd")}</div><div class="tiny muted">${state.fulfillment === "delivery" ? t("Haydovchiga beriladi (dorilar + yetkazish)") : t("Dorixonada to'lanadi")}</div></div></label>
      ${state.method === "card" ? `
        <div class="mt8">${cards.map((k) => `<label class="radio-card ${state.cardId === k.id ? "active" : ""}"><input type="radio" name="card" value="${k.id}" ${state.cardId === k.id ? "checked" : ""}>
          <div><div class="bold small">${esc(k.brand)} ${esc(k.masked)}</div><div class="tiny muted">${esc(k.expiry)}</div></div></label>`).join("")}
          <button class="btn secondary sm" id="addCard">+ ${t("Karta qo'shish")}</button></div>` : ""}

      <div class="card mt16" id="totals"><div class="spinner" style="margin:10px auto"></div></div>
      <button class="btn" id="checkout">${t("Buyurtma berish")}</button>
      <div style="height:10px"></div>`;

    c.querySelectorAll("[data-inc]").forEach((b) => (b.onclick = () => { const i = cart.items.find((x) => x.inventory_id == b.dataset.inc); cart.setQty(i.inventory_id, i.quantity + 1); draw(); schedQuote(); }));
    c.querySelectorAll("[data-dec]").forEach((b) => (b.onclick = () => { const i = cart.items.find((x) => x.inventory_id == b.dataset.dec); cart.setQty(i.inventory_id, i.quantity - 1); draw(); schedQuote(); }));
    c.querySelectorAll("#ful button").forEach((b) => { b.classList.toggle("active", b.dataset.v === state.fulfillment); b.onclick = () => { state.fulfillment = b.dataset.v; draw(); schedQuote(); }; });
    c.querySelector("#addr")?.addEventListener("input", (e) => (state.address = e.target.value));
    c.querySelectorAll('input[name="pm"]').forEach((r) => (r.onchange = () => { state.method = r.value; draw(); drawTotals(); }));
    c.querySelectorAll('input[name="card"]').forEach((r) => (r.onchange = () => { state.cardId = Number(r.value); draw(); drawTotals(); }));
    c.querySelectorAll('input[name="rx"]').forEach((r) => (r.onchange = () => { state.rxId = Number(r.value); draw(); drawTotals(); }));
    c.querySelector("#addCard")?.addEventListener("click", async () => { const k = await addCardFlow(); cards.push(k); state.cardId = k.id; draw(); drawTotals(); });
    c.querySelector("#newRx")?.addEventListener("click", () => go("health", { upload: true }));
    c.querySelector("#checkout").onclick = checkout;
    drawTotals();
  }

  function drawTotals() {
    const el = c.querySelector("#totals");
    if (!el) return;
    if (!quote) { el.innerHTML = `<div class="spinner" style="margin:10px auto"></div>`; return; }
    el.innerHTML = `
      <div class="row small"><span class="muted">${t("Dorilar")}</span><span>${som(quote.items_total)}</span></div>
      ${state.fulfillment === "delivery" ? `<div class="row small mt8"><span class="muted">${t("Yetkazish ({n} dorixona, {km} km)", { n: quote.pharmacies, km: quote.distance_km })}</span><span>${som(quote.delivery_fee)}</span></div>` : ""}
      <div class="row mt12" style="font-size:18px"><b>${t("Jami")}</b><b>${som(quote.total)}</b></div>`;
    const btn = c.querySelector("#checkout");
    btn.textContent = state.method === "card" ? t("To'lash · {s}", { s: som(quote.total) }) : t("Buyurtma berish · {s}", { s: som(quote.total) });
  }

  const schedQuote = () => { clearTimeout(qTimer); qTimer = setTimeout(requote, 200); };

  async function checkout(e) {
    if (state.fulfillment === "delivery" && !state.address.trim()) return toast(t("Manzilni yozing"));
    if (state.method === "card" && !state.cardId) return toast(t("Karta tanlang yoki qo'shing"));
    if (cart.hasRx && !state.rxId) return toast(t("Retseptni biriktiring"));
    e.target.disabled = true;
    try {
      const order = await api("/orders/", { method: "POST", body: {
        items: cart.items.map((i) => ({ inventory_id: i.inventory_id, quantity: i.quantity })),
        fulfillment: state.fulfillment, payment_method: state.method, address: state.address,
        lat: loc.lat, lng: loc.lng, prescription_id: state.rxId } });
      if (state.method === "card") {
        try { await api(`/payments/orders/${order.id}/pay/`, { method: "POST", body: { card_id: state.cardId } }); }
        catch (err) { cart.clear(); toast(err.message, 4000); return go("orders", { order: order.id }); }
      }
      cart.clear();
      toast(state.method === "card" ? t("To'landi ✓ Buyurtma qabul qilindi") : t("Buyurtma qabul qilindi ✓"));
      go("orders", { order: order.id });
    } catch (err) { toast(err.message, 4000); e.target.disabled = false; }
  }

  draw();
  loadSide();
  requote();
  return () => clearTimeout(qTimer);
}
