// Bildirishnomalar: dori paydo bo'ldi, buyurtma holati, keshbek
import { api } from "../api.js";
import { st, t } from "../i18n.js";
import { dt, esc, icons, som } from "../ui.js";

export function notifView(n) {
  const d = n.data || {};
  if (n.kind === "back_in_stock") return { tone: "tone-mint", icon: icons.bell,
    title: t("{name} paydo bo'ldi!", { name: d.medicine }), body: t("{ph} dorixonasida {n} dona", { ph: d.pharmacy, n: d.quantity }), go: ["search"] };
  if (n.kind === "points") return { tone: "tone-violet", icon: icons.gift,
    title: t("+{n} ball keshbek", { n: d.points }), body: t("Buyurtma #{id} uchun. 1 ball = 1 so'm", { id: d.order_id }), go: ["orders", { order: d.order_id }] };
  return { tone: "tone-amber", icon: icons.bag,
    title: t("Buyurtma #{id}", { id: d.order_id }), body: st(d.status), go: ["orders", { order: d.order_id }] };
}

export function render(root, { go }) {
  root.innerHTML = `<header class="topbar"><div class="row start" style="gap:10px"><button class="icon-btn" id="back">←</button><h1>${t("Xabarlar")}</h1></div></header>
    <div class="screen"><div id="c"><div class="spinner"></div></div></div>`;
  root.querySelector("#back").onclick = () => go("home");
  const c = root.querySelector("#c");
  (async () => {
    try {
      const r = await api("/notifications/");
      c.innerHTML = r.items.length ? `<div class="card">${r.items.map((n, i) => {
        const v = notifView(n);
        return `<div class="notif ${n.is_read ? "" : "unread"}" data-i="${i}" style="cursor:pointer">
          <div class="ic ${v.tone}">${v.icon}</div>
          <div class="grow"><div class="t small">${esc(v.title)}</div><div class="tiny muted">${esc(v.body)}</div></div>
          <div class="tiny muted">${dt(n.created_at)}</div></div>`;
      }).join("")}</div>` : `<div class="empty"><div class="ic">🔔</div>${t("Hozircha xabar yo'q")}</div>`;
      c.querySelectorAll("[data-i]").forEach((el) => (el.onclick = () => go(...notifView(r.items[el.dataset.i]).go)));
      if (r.unread) api("/notifications/read/", { method: "POST" }).catch(() => {});
    } catch (e) { c.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  })();
  void som;
}
