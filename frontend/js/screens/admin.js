// Platforma administratori: hamma narsani ko'radi
import { api } from "../api.js";
import { st, t } from "../i18n.js";
import { dt, esc, som, toast } from "../ui.js";

const header = (title, sub = "Administrator") => `<header class="topbar"><div><h1>${t(title)}</h1><div class="sub">${t(sub)}</div></div>
  <div class="actions"><a class="btn sm secondary" href="/admin/" target="_blank" rel="noopener">Django admin ↗</a></div></header>`;

export const dashboard = {
  render(root, { go }) {
    root.innerHTML = `${header("Bosh sahifa")}<div class="screen" id="c"><div class="spinner"></div></div>`;
    const c = root.querySelector("#c");
    async function load() {
      try {
        const d = await api("/admin/stats/");
        const max = Math.max(1, ...d.week.map((w) => w.revenue));
        const u = d.users;
        c.innerHTML = `
          <div class="stat-grid">
            <div class="stat"><div class="v" style="color:var(--primary)">${som(d.revenue_today)}</div><div class="k">${t("Bugungi tushum")}</div></div>
            <div class="stat"><div class="v">${d.orders_today}</div><div class="k">${t("Bugungi buyurtmalar")}</div></div>
            <div class="stat" data-go="orders"><div class="v" style="color:var(--warn)">${d.orders_active}</div><div class="k">${t("Faol buyurtmalar")}</div></div>
            <div class="stat"><div class="v" style="color:var(--danger)">${d.deliveries_waiting}</div><div class="k">${t("Haydovchi kutmoqda")}</div></div>
            <div class="stat"><div class="v">${d.drivers_online}/${d.drivers_total}</div><div class="k">${t("Onlayn haydovchilar")}</div></div>
            <div class="stat"><div class="v">${d.reservations_active}</div><div class="k">${t("Faol bronlar")}</div></div>
            <div class="stat"><div class="v">${som(d.revenue_total)}</div><div class="k">${t("Jami tushum")}</div></div>
            <div class="stat"><div class="v">${som(d.platform_earning)}</div><div class="k">${t("Platforma komissiyasi")}</div></div>
          </div>
          <div class="card"><div class="bold small">${t("So'nggi 7 kun: tushum")}</div>
            <div class="bar-chart">${d.week.map((w) => `<div class="b" title="${som(w.revenue)} · ${w.orders}"><i style="height:${Math.round((w.revenue / max) * 100)}%"></i><span>${w.date.slice(8)}</span></div>`).join("")}</div></div>
          <div class="card"><div class="bold small">${t("Foydalanuvchilar")}</div>
            <table class="table-mini mt8">${["customer", "pharmacy", "driver", "taxipark", "admin"].map((r) => `<tr><td>${esc(st(r))}</td><td style="text-align:right"><b>${u[r] || 0}</b></td></tr>`).join("")}
            <tr><td>${t("Dorixonalar (faol)")}</td><td style="text-align:right"><b>${d.pharmacies_active}/${d.pharmacies}</b></td></tr>
            <tr><td>${t("Taksoparklar")}</td><td style="text-align:right"><b>${d.taxi_parks}</b></td></tr>
            <tr><td>${t("Tugagan qoldiq pozitsiyalari")}</td><td style="text-align:right"><b>${d.out_of_stock_items}</b></td></tr></table></div>`;
        c.querySelectorAll("[data-go]").forEach((el) => (el.onclick = () => go(el.dataset.go)));
      } catch (e) { c.innerHTML = esc(e.message); }
    }
    load();
    const tm = setInterval(load, 20000);
    return () => clearInterval(tm);
  },
};

export const users = {
  render(root) {
    let role = "", q = "";
    root.innerHTML = `${header("Foydalanuvchilar")}<div class="screen">
      <input class="input" id="q" placeholder="${t("Ism, login yoki telefon")}">
      <div class="seg mt8" id="roles" style="overflow-x:auto">${["", "customer", "pharmacy", "driver", "taxipark", "admin"].map((r) => `<button data-v="${r}">${r ? esc(st(r)) : t("Hammasi")}</button>`).join("")}</div>
      <div id="c" class="mt12"><div class="spinner"></div></div></div>`;
    const c = root.querySelector("#c");
    let timer;
    const segs = () => root.querySelectorAll("#roles button").forEach((b) => b.classList.toggle("active", b.dataset.v === role));
    root.querySelectorAll("#roles button").forEach((b) => (b.onclick = () => { role = b.dataset.v; segs(); load(); }));
    root.querySelector("#q").oninput = (e) => { q = e.target.value; clearTimeout(timer); timer = setTimeout(load, 300); };
    segs();
    async function load() {
      try {
        const rows = await api("/admin/users/", { query: { role, q } });
        c.innerHTML = rows.map((u) => `
          <div class="card" style="${u.is_active ? "" : "opacity:.55"}"><div class="row"><div style="min-width:0"><div class="bold">${esc(u.name || u.username)} <span class="tiny muted">@${esc(u.username)}</span></div>
            <div class="small muted">${esc(st(u.role))}${u.pharmacy ? " · " + esc(u.pharmacy) : ""}${u.taxi_park ? " · " + esc(u.taxi_park) : ""}${u.phone ? " · " + esc(u.phone) : ""}</div>
            <div class="tiny muted">${t("Buyurtmalar")}: ${u.orders} · ${dt(u.date_joined)}</div></div>
            <button class="btn sm ${u.is_active ? "danger" : ""}" data-t="${u.id}">${u.is_active ? t("Bloklash") : t("Faollashtirish")}</button></div></div>`).join("") || `<div class="empty">${t("Topilmadi")}</div>`;
        c.querySelectorAll("[data-t]").forEach((b) => (b.onclick = async () => {
          try { await api(`/admin/users/${b.dataset.t}/toggle/`, { method: "POST" }); load(); } catch (e) { toast(e.message); }
        }));
      } catch (e) { c.innerHTML = esc(e.message); }
    }
    load();
    return () => clearTimeout(timer);
  },
};

export const orders = {
  render(root) {
    let tab = "orders";
    root.innerHTML = `${header("Buyurtmalar")}<div class="screen">
      <div class="seg" id="seg"><button data-v="orders">${t("Buyurtmalar")}</button><button data-v="payments">${t("To'lovlar")}</button><button data-v="reservations">${t("Bronlar")}</button></div>
      <div id="c" class="mt12"><div class="spinner"></div></div></div>`;
    const c = root.querySelector("#c");
    const segs = () => root.querySelectorAll("#seg button").forEach((b) => b.classList.toggle("active", b.dataset.v === tab));
    root.querySelectorAll("#seg button").forEach((b) => (b.onclick = () => { tab = b.dataset.v; segs(); load(); }));
    segs();
    async function load() {
      try {
        if (tab === "orders") {
          const rows = await api("/admin/orders/");
          c.innerHTML = rows.map((o) => `
            <div class="card"><div class="row"><b>#${o.id} · ${som(o.total)}</b><span class="chip ${o.status === "completed" ? "ok" : o.status === "cancelled" ? "danger" : "warn"}">${esc(st(o.status))}</span></div>
              <div class="small muted mt8">👤 ${esc(o.customer.name)} · ${esc(st(o.fulfillment))} · ${esc(st(o.payment_method))} · ${esc(st(o.payment_status || ""))}</div>
              ${o.pharmacy_orders.map((p) => `<div class="row tiny mt8"><span>🏥 ${esc(p.pharmacy.name)} · ${p.items.map((i) => esc(i.medicine_name) + "×" + i.quantity).join(", ")}</span><span class="chip">${esc(st(p.status))}</span></div>`).join("")}
              ${o.delivery ? `<div class="tiny muted mt8">🚕 ${esc(st(o.delivery.status))}${o.delivery.driver ? " · " + esc(o.delivery.driver.name) + " (" + esc(o.delivery.driver.park) + ")" : ""} · ${som(o.delivery.fee)}</div>` : ""}
              <div class="tiny muted mt8">${dt(o.created_at)}</div></div>`).join("") || `<div class="empty">${t("Hali buyurtma yo'q")}</div>`;
        } else if (tab === "payments") {
          const rows = await api("/admin/payments/");
          c.innerHTML = `<div class="card">${rows.map((p) => `<div class="list-row"><div><b>${som(p.amount)}</b> <span class="tiny muted">#${p.order_id} · ${esc(p.customer)}</span>
            <div class="tiny muted">${esc(st(p.method))}${p.card ? " · " + esc(p.card) : ""} · ${esc(p.provider)} · ${dt(p.created_at)}</div></div>
            <span class="chip ${p.status === "paid" ? "ok" : p.status === "failed" ? "danger" : ""}">${esc(st(p.status))}</span></div>`).join("") || t("Yo'q")}</div>`;
        } else {
          const rows = await api("/admin/reservations/");
          c.innerHTML = `<div class="card">${rows.map((r) => `<div class="list-row"><div><b>${esc(r.medicine)}</b> × ${r.quantity}
            <div class="tiny muted">${esc(r.customer)} · ${esc(r.pharmacy)} · ${r.hold_minutes} ${t("daq")} · ${dt(r.created_at)}</div></div>
            <span class="chip">${esc(st(r.status))}</span></div>`).join("") || t("Yo'q")}</div>`;
        }
      } catch (e) { c.innerHTML = esc(e.message); }
    }
    load();
  },
};

export const partners = {
  render(root) {
    let tab = "pharmacies";
    root.innerHTML = `${header("Hamkorlar")}<div class="screen">
      <div class="seg" id="seg"><button data-v="pharmacies">🏥 ${t("Dorixonalar")}</button><button data-v="taxi">🚕 ${t("Taksi")}</button></div>
      <div id="c" class="mt12"><div class="spinner"></div></div></div>`;
    const c = root.querySelector("#c");
    const segs = () => root.querySelectorAll("#seg button").forEach((b) => b.classList.toggle("active", b.dataset.v === tab));
    root.querySelectorAll("#seg button").forEach((b) => (b.onclick = () => { tab = b.dataset.v; segs(); load(); }));
    segs();
    async function load() {
      try {
        if (tab === "pharmacies") {
          const rows = await api("/admin/pharmacies/");
          c.innerHTML = rows.map((p) => `
            <div class="card" style="${p.is_active ? "" : "opacity:.55"}"><div class="row"><div><div class="bold">${esc(p.name)} ${p.is_24h ? '<span class="chip">24/7</span>' : ""}</div>
              <div class="tiny muted">${esc(p.address)} · ${esc(p.phone)}</div>
              <div class="small mt8">${t("Pozitsiyalar")}: <b>${p.items}</b> · ${t("Tugagan")}: <b style="color:var(--danger)">${p.out_of_stock}</b> · ${t("Bugun")}: <b>${p.orders_today}</b></div></div>
              <button class="btn sm ${p.is_active ? "danger" : ""}" data-p="${p.id}">${p.is_active ? t("O'chirish") : t("Yoqish")}</button></div></div>`).join("");
          c.querySelectorAll("[data-p]").forEach((b) => (b.onclick = async () => { await api(`/admin/pharmacies/${b.dataset.p}/toggle/`, { method: "POST" }); load(); }));
        } else {
          const d = await api("/admin/taxi/");
          c.innerHTML = `${d.parks.map((p) => `
            <div class="card"><div class="row"><div><div class="bold">🏢 ${esc(p.name)}</div><div class="tiny muted">${esc(p.phone)} · ${t("komissiya")} ${p.commission_percent}%</div></div>
              <span class="chip ok">${p.online}/${p.drivers} ${t("onlayn")}</span></div>
              <div class="small mt8">${t("Bugun")}: <b>${p.today_deliveries}</b> · ${t("Aylanma")}: <b>${som(p.turnover)}</b></div></div>`).join("")}
            <div class="section-title">${t("Haydovchilar")}</div>
            <div class="card">${d.drivers.map((x) => `<div class="list-row"><div><b>${x.is_online ? "🟢" : "⚪"} ${esc(x.name)}</b> <span class="tiny muted">${esc(x.park)}</span>
              <div class="tiny muted">${esc(x.car)} · ${esc(x.phone)} · ${t("yetkazgan")}: ${x.delivered}</div></div>${x.busy ? `<span class="chip warn">${t("Band")}</span>` : ""}</div>`).join("")}</div>`;
        }
      } catch (e) { c.innerHTML = esc(e.message); }
    }
    load();
  },
};
