// Dorixona paneli: bosh sahifa, buyurtmalar + bronlar, ombor + muddati yaqin dorilar
import { api, auth } from "../api.js";
import { st, t } from "../i18n.js";
import { closeSheet, countdown, dt, esc, sheet, som, toast } from "../ui.js";

const stockoutText = (h) => {
  if (h === null || h === undefined) return t("sotuv yo'q");
  if (h < 1) return t("~{m} daqiqada tugaydi", { m: Math.max(1, Math.round(h * 60)) });
  if (h < 48) return t("~{h} soatda tugaydi", { h: Math.round(h) });
  return t("~{d} kunga yetadi", { d: Math.round(h / 24) });
};
const levelChip = (r) => r.level === "out" ? `<span class="chip danger">${t("Tugagan")}</span>`
  : r.level === "low" ? `<span class="chip warn">${t("Kam qoldi")}</span>` : `<span class="chip ok">${t("Yetarli")}</span>`;
const expChip = (d) => d === null || d === undefined ? "" : d < 0 ? `<span class="chip danger">${t("Muddati o'tgan")}</span>`
  : d <= 30 ? `<span class="chip danger">${t("{d} kun qoldi", { d })}</span>` : d <= 90 ? `<span class="chip warn">${t("{d} kun qoldi", { d })}</span>` : "";

const header = (title) => `<header class="topbar"><div><h1>${t(title)}</h1><div class="sub">${esc(auth.user?.pharmacy_name || "")}</div></div></header>`;

// ================= BOSH SAHIFA =================
export const dashboard = {
  render(root, { go }) {
    root.innerHTML = `${header("Bosh sahifa")}<div class="screen" id="c"><div class="spinner"></div></div>`;
    const c = root.querySelector("#c");
    async function load() {
      try {
        const d = await api("/panel/dashboard/");
        c.innerHTML = `
          <div class="stat-grid">
            <div class="stat" data-go="orders"><div class="v" style="color:var(--primary)">${d.new_orders}</div><div class="k">${t("Yangi buyurtmalar")}</div></div>
            <div class="stat" data-go="orders"><div class="v" style="color:var(--primary)">${d.active_reservations}</div><div class="k">${t("Faol bronlar")}</div></div>
            <div class="stat" data-go="inventory"><div class="v" style="color:var(--warn)">${d.low_stock}</div><div class="k">${t("Kam qolgan")}</div></div>
            <div class="stat" data-go="inventory"><div class="v" style="color:var(--danger)">${d.out_of_stock}</div><div class="k">${t("Tugagan")}</div></div>
            <div class="stat" data-go="expiring"><div class="v" style="color:var(--danger)">${d.expiring}</div><div class="k">${t("Muddati yaqin")}</div></div>
            <div class="stat"><div class="v">${d.sold_today}</div><div class="k">${t("Bugun sotildi (dona)")}</div></div>
          </div>
          <div class="section-title">${t("AI ogohlantirishlar — buyurtma bering")}</div>
          ${d.alerts.length ? d.alerts.map((r) => `
            <div class="card"><div class="row"><div><div class="bold">${esc(r.medicine.name)} ${esc(r.medicine.dosage)}</div>
              <div class="small muted">${t("{n} dona · soatiga ~{r} sotiladi", { n: r.available, r: r.sales_per_hour })}</div></div>${levelChip(r)}</div>
              <div class="small mt8" style="color:${r.level === "out" ? "var(--danger)" : "var(--warn)"};font-weight:700">${r.level === "out" ? t("Mijozlar qidirmoqda — qoldiqni to'ldiring") : "⏱ " + stockoutText(r.hours_until_stockout)}</div>
            </div>`).join("") : `<div class="empty">${t("Hammasi joyida ✅")}</div>`}`;
        c.querySelectorAll("[data-go]").forEach((el) => (el.onclick = () =>
          el.dataset.go === "expiring" ? go("inventory", { tab: "expiring" }) : go(el.dataset.go)));
      } catch (e) { c.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
    }
    load();
    const tm = setInterval(load, 20000);
    return () => clearInterval(tm);
  },
};

// ================= BUYURTMALAR + BRONLAR =================
export const orders = {
  render(root, { params }) {
    let tab = params?.tab || "orders";
    root.innerHTML = `${header("Buyurtmalar")}<div class="screen">
      <div class="seg" id="seg"><button data-v="orders">${t("Buyurtmalar")}</button><button data-v="reservations">${t("Bronlar")}</button></div>
      <div id="c" class="mt12"><div class="spinner"></div></div></div>`;
    const c = root.querySelector("#c");
    const segs = () => root.querySelectorAll("#seg button").forEach((b) => b.classList.toggle("active", b.dataset.v === tab));
    root.querySelectorAll("#seg button").forEach((b) => (b.onclick = () => { tab = b.dataset.v; segs(); load(); }));
    segs();

    const load = () => (tab === "orders" ? loadOrders() : loadRes());

    async function loadOrders() {
      let rows;
      try { rows = await api("/panel/orders/"); } catch (e) { c.innerHTML = esc(e.message); return; }
      const active = rows.filter((r) => ["new", "accepted", "ready"].includes(r.status));
      const past = rows.filter((r) => !["new", "accepted", "ready"].includes(r.status)).slice(0, 20);
      c.innerHTML = `
        <div class="section-title">${t("Faol")} (${active.length})</div>
        ${active.map((r) => `
          <div class="card ${r.status === "new" ? "recommended" : ""}">
            <div class="row"><b>#${r.order_id} · ${som(r.subtotal)}</b><span class="chip ${r.status === "ready" ? "ok" : "warn"}">${esc(st(r.status))}</span></div>
            <div class="small muted">${esc(r.customer)} ${r.customer_phone ? "· " + esc(r.customer_phone) : ""} · ${r.fulfillment === "delivery" ? "🚕 " + t("Yetkazish") : "🏥 " + t("O'zi oladi")} · ${esc(st(r.payment_method))}${r.is_paid ? " ✓" : ""}</div>
            <div class="mt8">${r.items.map((i) => `<div class="row small"><span>${esc(i.name)} × <b>${i.quantity}</b> ${i.rx ? '<span class="chip warn">Rx</span>' : ""}</span><span class="muted">${som(i.price * i.quantity)}</span></div>`).join("")}</div>
            ${r.has_rx ? `<div class="hint ${r.rx_verified ? "" : "urgent"} mt8 small">${r.rx_verified ? "✓ " + t("Retsept tekshirildi") : t("Retseptli dori — retseptni tekshiring")}
              ${r.prescription_image ? ` · <a href="${esc(r.prescription_image)}" target="_blank" rel="noopener">${t("Rasmni ko'rish")}</a>` : ""}
              ${r.prescription_text ? `<div class="tiny muted mt8" style="white-space:pre-wrap">${esc(r.prescription_text.slice(0, 300))}</div>` : ""}</div>` : ""}
            ${r.driver ? `<div class="tiny muted mt8">🚕 ${esc(r.driver)}</div>` : ""}
            <div class="btn-row mt12">
              ${r.has_rx && !r.rx_verified ? `<button class="btn sm" data-a="verify_rx" data-id="${r.id}">${t("Retsept to'g'ri")}</button>` : ""}
              ${r.status === "new" ? `<button class="btn sm" data-a="accept" data-id="${r.id}">${t("Qabul qilish")}</button>` : ""}
              ${["new", "accepted"].includes(r.status) ? `<button class="btn sm" data-a="ready" data-id="${r.id}">${t("Tayyor")}</button>` : ""}
              ${r.status === "ready" && r.fulfillment === "pickup" ? `<button class="btn sm" data-a="issue" data-id="${r.id}">${t("Berish (kod)")}</button>` : ""}
              ${r.status === "ready" && r.fulfillment === "delivery" ? `<span class="small muted" style="align-self:center">${t("Haydovchini kuting")}</span>` : ""}
              <button class="btn sm danger" data-a="reject" data-id="${r.id}">${t("Rad etish")}</button>
            </div>
          </div>`).join("") || `<div class="empty"><div class="ic">📭</div>${t("Hozircha yangi buyurtma yo'q")}</div>`}
        ${past.length ? `<div class="section-title">${t("Tarix")}</div>${past.map((r) => `
          <div class="card"><div class="row"><div><b>#${r.order_id}</b> <span class="small muted">${som(r.subtotal)}</span><div class="tiny muted">${dt(r.created_at)}</div></div><span class="chip">${esc(st(r.status))}</span></div></div>`).join("")}` : ""}`;
      c.querySelectorAll("[data-a]").forEach((b) => (b.onclick = () => act(b.dataset.id, b.dataset.a)));
    }

    async function act(id, a) {
      if (a === "issue") return codeSheet(t("Mijoz aytgan 4 xonali kodni kiriting"), (code) => api(`/panel/orders/${id}/issue/`, { method: "POST", body: { code } }));
      try { await api(`/panel/orders/${id}/${a}/`, { method: "POST" }); load(); } catch (e) { toast(e.message); }
    }

    function codeSheet(label, fn) {
      const sh = sheet(`<div class="bold" style="font-size:20px">${t("Mijozga berish")}</div><div class="small muted mt8">${label}</div>
        <input class="input mt16" id="code" inputmode="numeric" maxlength="4" style="font-size:28px;text-align:center;letter-spacing:10px">
        <button class="btn mt16" id="ok">${t("Tasdiqlash va berish")}</button>`);
      sh.querySelector("#code").focus();
      sh.querySelector("#ok").onclick = async () => {
        try { await fn(sh.querySelector("#code").value); closeSheet(); toast(t("Berildi — qoldiq avtomatik kamaydi")); load(); }
        catch (e) { toast(e.message); }
      };
    }

    async function loadRes() {
      let items;
      try { items = await api("/panel/reservations/"); } catch (e) { c.innerHTML = esc(e.message); return; }
      const active = items.filter((r) => ["pending", "confirmed"].includes(r.status));
      const past = items.filter((r) => !["pending", "confirmed"].includes(r.status)).slice(0, 20);
      c.innerHTML = `
        <div class="section-title">${t("Faol")} (${active.length})</div>
        ${active.map((r) => `
          <div class="card ${r.status === "pending" ? "recommended" : ""}">
            <div class="row"><span class="chip ${r.status === "confirmed" ? "ok" : "warn"}">${esc(st(r.status))}</span><b data-cd="${esc(r.expires_at)}">${countdown(r.expires_at)}</b></div>
            <div class="bold mt12" style="font-size:17px">${esc(r.medicine.name)} ${esc(r.medicine.dosage)} × ${r.quantity}</div>
            <div class="small muted">${esc(r.customer || "")} ${r.customer_phone ? "· " + esc(r.customer_phone) : ""}</div>
            <div class="btn-row mt12">
              ${r.status === "pending" ? `<button class="btn sm" data-r="confirm" data-id="${r.id}">${t("Tayyorladim")}</button>` : ""}
              <button class="btn sm ${r.status === "pending" ? "secondary" : ""}" data-r="complete" data-id="${r.id}">${t("Berish (kod)")}</button>
              <button class="btn sm danger" data-r="cancel" data-id="${r.id}">${t("Bekor")}</button>
            </div>
          </div>`).join("") || `<div class="empty"><div class="ic">📭</div>${t("Hozircha faol bron yo'q")}</div>`}
        ${past.length ? `<div class="section-title">${t("Tarix")}</div>${past.map((r) => `
          <div class="card"><div class="row"><div><div class="bold">${esc(r.medicine.name)} × ${r.quantity}</div>
          <div class="tiny muted">${dt(r.created_at)}</div></div><span class="chip">${esc(st(r.status))}</span></div></div>`).join("")}` : ""}`;
      c.querySelectorAll("[data-r]").forEach((b) => (b.onclick = async () => {
        if (b.dataset.r === "complete") return codeSheet(t("Mijoz aytgan 4 xonali kodni kiriting"), (code) => api(`/panel/reservations/${b.dataset.id}/complete/`, { method: "POST", body: { code } }));
        try { await api(`/panel/reservations/${b.dataset.id}/${b.dataset.r}/`, { method: "POST" }); load(); } catch (e) { toast(e.message); }
      }));
    }

    const tick = setInterval(() => c.querySelectorAll("[data-cd]").forEach((el) => (el.textContent = countdown(el.dataset.cd))), 1000);
    const poll = setInterval(() => { if (!document.querySelector(".sheet")) load(); }, 10000);
    load();
    return () => { clearInterval(tick); clearInterval(poll); };
  },
};

// ================= OMBOR + MUDDATI YAQIN =================
export const inventory = {
  render(root, { params }) {
    let tab = params?.tab || "stock";
    root.innerHTML = `${header("Ombor")}<div class="screen">
      <div class="seg" id="seg"><button data-v="stock">${t("Qoldiq")}</button><button data-v="expiring">⏳ ${t("Muddati yaqin")}</button></div>
      <div id="c" class="mt12"><div class="spinner"></div></div></div>`;
    const c = root.querySelector("#c");
    const segs = () => root.querySelectorAll("#seg button").forEach((b) => b.classList.toggle("active", b.dataset.v === tab));
    root.querySelectorAll("#seg button").forEach((b) => (b.onclick = () => { tab = b.dataset.v; segs(); load(); }));
    segs();
    let rows = [], filter = "";
    const load = () => (tab === "stock" ? loadStock() : loadExpiring());

    async function loadStock() {
      try { rows = await api("/panel/inventory/"); } catch (e) { c.innerHTML = esc(e.message); return; }
      c.innerHTML = `<input class="input" id="f" placeholder="${t("Dori nomi bo'yicha filtr")}" value="${esc(filter)}"><div id="list" class="mt12"></div>`;
      c.querySelector("#f").oninput = (e) => { filter = e.target.value; drawStock(); };
      drawStock();
    }
    function drawStock() {
      const list = rows.filter((r) => r.medicine.name.toLowerCase().includes(filter.toLowerCase()));
      c.querySelector("#list").innerHTML = list.map((r) => `
        <div class="card" data-id="${r.id}" style="cursor:pointer">
          <div class="row"><div><div class="bold">${esc(r.medicine.name)} ${esc(r.medicine.dosage)}</div>
            <div class="small muted">${esc(r.medicine.form)} · ${som(r.final_price)}${r.discount_percent ? ` <span class="chip disc">−${r.discount_percent}%</span>` : ""}</div></div>
            <div style="text-align:right"><div class="bold" style="font-size:20px">${r.available}</div>
            <div class="tiny muted">${r.reserved ? t("{n} bronda", { n: r.reserved }) : t("dona")}</div></div></div>
          <div class="row mt8"><span>${levelChip(r)} ${expChip(r.days_to_expiry)}</span><span class="tiny muted">${r.available === 0 ? t("Qoldiqni to'ldiring") : stockoutText(r.hours_until_stockout)}</span></div>
        </div>`).join("") || `<div class="empty">${t("Topilmadi")}</div>`;
      c.querySelectorAll("[data-id]").forEach((el) => (el.onclick = () => edit(rows.find((r) => r.id == el.dataset.id))));
    }

    async function loadExpiring() {
      let d;
      try { d = await api("/panel/expiring/"); } catch (e) { c.innerHTML = esc(e.message); return; }
      rows = d.items;
      c.innerHTML = `
        <div class="stat-grid">
          <div class="stat"><div class="v" style="color:var(--danger)">${d.items.length}</div><div class="k">${t("{n} kun ichida tugaydi", { n: d.days })}</div></div>
          <div class="stat"><div class="v" style="color:var(--warn)">${som(d.total_loss_at_risk)}</div><div class="k">${t("Sotilmay qolishi mumkin")}</div></div>
        </div>
        <div class="hint small">${t("Sotuv tezligiga qarab muddatgacha sotilmay qoladigan qism hisoblangan. Chegirma qo'ysangiz, mijozlar qidiruvda ko'radi.")}</div>
        <div class="mt12">${d.items.map((r) => `
          <div class="card">
            <div class="row"><div><div class="bold">${esc(r.medicine.name)} ${esc(r.medicine.dosage)}</div>
              <div class="tiny muted">${t("Muddat")}: ${esc(r.expiry_date)} · ${r.quantity} ${t("dona")}</div></div>${expChip(r.days_to_expiry)}</div>
            <div class="small mt8">${r.units_at_risk ? `⚠ ${t("~{n} dona sotilmay qolishi mumkin ({s})", { n: r.units_at_risk, s: som(r.loss_at_risk) })}` : `✓ ${t("Muddatgacha sotilib ketadi")}`}</div>
            <div class="row mt12"><span class="small">${t("Chegirma")}: <b>${r.discount_percent}%</b> ${r.suggested_discount && r.suggested_discount !== r.discount_percent ? `<span class="muted">(${t("tavsiya")}: ${r.suggested_discount}%)</span>` : ""}</span>
              <div class="btn-row">${r.suggested_discount && r.suggested_discount !== r.discount_percent ? `<button class="btn sm" data-disc="${r.id}|${r.suggested_discount}">−${r.suggested_discount}%</button>` : ""}
              <button class="btn sm secondary" data-id="${r.id}">${t("Tahrirlash")}</button></div></div>
          </div>`).join("") || `<div class="empty">✅ ${t("Muddati yaqin dori yo'q")}</div>`}</div>`;
      c.querySelectorAll("[data-disc]").forEach((b) => (b.onclick = async () => {
        const [id, v] = b.dataset.disc.split("|");
        try { await api(`/panel/inventory/${id}/`, { method: "PATCH", body: { discount_percent: v } }); toast(t("Chegirma qo'yildi ✓")); load(); }
        catch (e) { toast(e.message); }
      }));
      c.querySelectorAll("[data-id]").forEach((el) => (el.onclick = () => edit(rows.find((r) => r.id == el.dataset.id))));
    }

    function edit(r) {
      const sh = sheet(`
        <div class="bold" style="font-size:20px">${esc(r.medicine.name)} ${esc(r.medicine.dosage)}</div>
        <div class="small muted mt8">${t("Bronda: {n} dona · soatiga ~{r} sotiladi", { n: r.reserved, r: r.sales_per_hour })}</div>
        <label class="lbl">${t("Qoldiq (dona)")}</label><input class="input" id="q" type="number" inputmode="numeric" min="0" value="${r.quantity}">
        <label class="lbl">${t("Narx (so'm)")}</label><input class="input" id="p" type="number" inputmode="numeric" min="0" value="${r.price}">
        <label class="lbl">${t("Chegirma (%)")}</label><input class="input" id="d" type="number" inputmode="numeric" min="0" max="90" value="${r.discount_percent}">
        <label class="lbl">${t("Minimal qoldiq")}</label><input class="input" id="m" type="number" inputmode="numeric" min="0" value="${r.min_stock}">
        <button class="btn mt16" id="save">${t("Saqlash")}</button>`);
      sh.querySelector("#save").onclick = async () => {
        try {
          await api(`/panel/inventory/${r.id}/`, { method: "PATCH", body: {
            quantity: sh.querySelector("#q").value, price: sh.querySelector("#p").value,
            discount_percent: sh.querySelector("#d").value, min_stock: sh.querySelector("#m").value } });
          closeSheet(); toast(t("Saqlandi ✓")); load();
        } catch (e) { toast(e.message); }
      };
    }
    load();
  },
};
