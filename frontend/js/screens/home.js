// Bosh sahifa: salomlashish, qidiruv, tez amallar, keyingi dori, faol buyurtma, ballar
import { api } from "../api.js";
import { st, t } from "../i18n.js";
import { countdown, esc, icons, som, toast } from "../ui.js";

export function render(root, { go }) {
  const h = new Date().getHours();
  const hello = h < 5 ? "Xayrli tun" : h < 12 ? "Xayrli tong" : h < 18 ? "Xayrli kun" : "Xayrli kech";
  root.innerHTML = `<div class="screen flush">
    <div class="hero">
      <div class="row"><div><div class="sub">${t(hello)} 👋</div><h1 id="nm">&nbsp;</h1></div>
        <div class="row" style="gap:8px"><span class="points-pill" id="pts">${icons.gift.replace("<svg", '<svg style="width:15px;height:15px"')} …</span>
          <button class="icon-btn" id="bell">${icons.bell}</button></div></div>
      <button class="hero-search" id="search">${icons.search}<span>${t("Dori nomi: paratsetamol, нурофен...")}</span>
        <span class="scan-ic" id="scan">${icons.scan}</span></button>
    </div>
    <div class="pad mt16">
      <div class="qa">
        <button class="qi" data-go="search"><div class="ic tone-mint">${icons.search}</div>${t("Qidiruv")}</button>
        <button class="qi" data-go="scan"><div class="ic tone-violet">${icons.scan}</div>${t("Retsept")}</button>
        <button class="qi" data-go="orders"><div class="ic tone-amber">${icons.bag}</div>${t("Buyurtmalar")}</button>
        <button class="qi" data-go="urgent"><div class="ic tone-coral">🚨</div>${t("Shoshilinch")}</button>
      </div>
      <div id="c" class="mt16"><div class="skeleton"></div><div class="skeleton"></div></div>
    </div></div>`;
  const $ = (s) => root.querySelector(s);
  $("#search").onclick = (e) => { if (!e.target.closest("#scan")) go("search"); };
  $("#scan").onclick = (e) => { e.stopPropagation(); go("scan"); };
  $("#bell").onclick = () => go("notifications");
  root.querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => {
    if (b.dataset.go === "urgent") { toast(t("Shoshilinch rejim: eng kafolatli dorixona birinchi")); go("search", { urgent: true }); }
    else go(b.dataset.go);
  }));

  let timer = null;
  async function load() {
    let d;
    try { d = await api("/home/"); } catch (e) { $("#c").innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
    $("#nm").textContent = d.name;
    $("#pts").innerHTML = `${icons.gift.replace("<svg", '<svg style="width:15px;height:15px"')} ${d.points.toLocaleString("ru-RU")}`;
    $("#bell").querySelector(".badge-dot")?.remove();
    if (d.unread) $("#bell").insertAdjacentHTML("beforeend", `<span class="badge-dot">${d.unread}</span>`);

    const o = d.active_order;
    const n = d.next_dose;
    $("#c").innerHTML = `
      ${o ? `<div class="section-title">${t("Faol buyurtma")}</div>
        <div class="card" id="order" style="cursor:pointer">
          <div class="row"><div class="row start" style="gap:10px"><span class="live-dot"></span><b>#${o.id} · ${esc(st(o.status))}</b></div>
            <span class="chip mint">${som(o.total)}</span></div>
          <div class="small muted mt8">${o.driver ? `🚕 ${esc(o.driver)} · ${esc(o.car)}` : o.fulfillment === "pickup" ? t("O'zim olib ketaman") : t("Haydovchi qidirilmoqda...")}
            · ${t("{n} ta dorixona", { n: o.pharmacies })}</div>
          <div class="bar mt12"><i style="width:${({ awaiting_payment: 8, confirmed: 22, preparing: 45, ready: 65, delivering: 85 })[o.status] || 30}%"></i></div>
        </div>` : ""}
      ${d.reservations.map((r) => `<div class="card tint"><div class="row"><div class="grow"><div class="tiny muted">${t("Bron")} · ${esc(r.pharmacy)}</div>
          <div class="bold">${esc(r.medicine)}</div></div>
          <div style="text-align:right"><div class="xbold" style="letter-spacing:3px">${esc(r.code)}</div><div class="tiny muted" data-cd="${esc(r.expires_at)}"></div></div></div></div>`).join("")}
      <div class="section-title">${t("Keyingi dori")}<button id="toHealth">${t("Jadval")} →</button></div>
      ${n ? `<div class="card"><div class="next-dose">
          <div class="qi" style="box-shadow:none;padding:0;background:none"><div class="ic tone-mint" style="margin:0;width:52px;height:52px;border-radius:16px">${icons.pill}</div></div>
          <div class="grow"><div class="time">${esc(n.time)}</div>
            <div class="small"><b>${esc(n.medicine_name)}</b> ${esc(n.dose)}</div>
            ${n.member ? `<div class="tiny muted">👤 ${esc(n.member)}</div>` : ""}</div>
          <button class="btn sm" id="take">${t("Ichdim")} ✓</button></div></div>`
        : `<div class="card"><div class="small muted">${t("Bugun boshqa qabul yo'q. Retsept yuklasangiz, eslatmalarni o'zimiz qo'yamiz.")}</div></div>`}
      <div class="promo"><div style="position:relative;z-index:1">
        <div class="chip" style="background:rgba(255,255,255,.2);color:#fff">✨ ${t("Yangi")}</div>
        <div class="bold mt8" style="font-size:18px">${t("Har xariddan 1% keshbek")}</div>
        <div class="small" style="opacity:.85">${t("Sizda {n} ball bor — keyingi buyurtmada ishlating.", { n: d.points.toLocaleString("ru-RU") })}</div></div></div>
      ${d.watching ? `<div class="card"><div class="row"><div class="small">🔔 ${t("{n} ta dori kuzatilmoqda — paydo bo'lsa xabar beramiz", { n: d.watching })}</div></div></div>` : ""}`;
    $("#order")?.addEventListener("click", () => go("orders", { order: o.id }));
    $("#toHealth").onclick = () => go("health");
    $("#take")?.addEventListener("click", async () => {
      try { await api(`/courses/${n.course_id}/log/`, { method: "POST", body: { time: n.time, status: "taken" } }); toast(t("Ajoyib! Belgilandi ✓")); load(); }
      catch (e) { toast(e.message); }
    });
    tick();
  }
  const tick = () => root.querySelectorAll("[data-cd]").forEach((el) => (el.textContent = countdown(el.dataset.cd)));
  load();
  timer = setInterval(tick, 1000);
  const poll = setInterval(load, 20000);
  return () => { clearInterval(timer); clearInterval(poll); };
}
