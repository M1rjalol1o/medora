// Ilova kirish nuqtasi: rolga qarab tablar va ekranlar.
import { auth } from "./api.js";
import { cart } from "./cart.js";
import { startAlarms, stopAlarms } from "./alarm.js";
import { setLang, currentLang, t } from "./i18n.js";
import { app, applyTheme, icons } from "./ui.js";
import * as loginScreen from "./screens/login.js";
import * as searchScreen from "./screens/search.js";
import * as cartScreen from "./screens/cart.js";
import * as ordersScreen from "./screens/orders.js";
import * as healthScreen from "./screens/health.js";
import * as profileScreen from "./screens/profile.js";
import * as pharmacy from "./screens/panel.js";
import * as driver from "./screens/driver.js";
import * as park from "./screens/park.js";
import * as admin from "./screens/admin.js";

const TABS = {
  customer: [
    { id: "search", label: "Qidiruv", icon: icons.search, screen: searchScreen },
    { id: "cart", label: "Savat", icon: icons.cart, screen: cartScreen, badge: () => cart.count },
    { id: "orders", label: "Buyurtmalar", icon: icons.bag, screen: ordersScreen },
    { id: "health", label: "Salomatlik", icon: icons.heart, screen: healthScreen },
    { id: "profile", label: "Profil", icon: icons.user, screen: profileScreen },
  ],
  pharmacy: [
    { id: "dashboard", label: "Bosh sahifa", icon: icons.home, screen: pharmacy.dashboard },
    { id: "orders", label: "Buyurtmalar", icon: icons.bag, screen: pharmacy.orders },
    { id: "inventory", label: "Ombor", icon: icons.box, screen: pharmacy.inventory },
    { id: "profile", label: "Profil", icon: icons.user, screen: profileScreen },
  ],
  driver: [
    { id: "tasks", label: "Topshiriqlar", icon: icons.car, screen: driver.tasks },
    { id: "earnings", label: "Daromad", icon: icons.wallet, screen: driver.earnings },
    { id: "profile", label: "Profil", icon: icons.user, screen: profileScreen },
  ],
  taxipark: [
    { id: "dashboard", label: "Bosh sahifa", icon: icons.home, screen: park.dashboard },
    { id: "drivers", label: "Haydovchilar", icon: icons.users, screen: park.drivers },
    { id: "deliveries", label: "Yetkazishlar", icon: icons.route, screen: park.deliveries },
    { id: "profile", label: "Profil", icon: icons.user, screen: profileScreen },
  ],
  admin: [
    { id: "dashboard", label: "Bosh sahifa", icon: icons.chart, screen: admin.dashboard },
    { id: "users", label: "Foydalanuvchilar", icon: icons.users, screen: admin.users },
    { id: "orders", label: "Buyurtmalar", icon: icons.bag, screen: admin.orders },
    { id: "partners", label: "Hamkorlar", icon: icons.store, screen: admin.partners },
    { id: "profile", label: "Profil", icon: icons.user, screen: profileScreen },
  ],
};

let current = null;
let unsubCart = null;

export function start() {
  applyTheme();
  document.documentElement.lang = currentLang();
  const user = auth.user;
  cleanup();
  if (!user || !auth.tokens) {
    stopAlarms();
    loginScreen.render(app(), { onLogin: start });
    return;
  }
  const tabs = TABS[user.role] || TABS.customer;
  const wanted = location.hash.slice(1);
  const first = tabs.find((x) => x.id === wanted) || tabs[0];
  app().innerHTML = `<div id="view" style="flex:1;display:flex;flex-direction:column;min-height:0"></div>
    <nav class="tabbar">${tabs.map((x) => `<button data-tab="${x.id}">${x.icon}<span>${t(x.label)}</span></button>`).join("")}</nav>`;
  app().querySelectorAll(".tabbar button").forEach((b) => (b.onclick = () => go(b.dataset.tab)));

  const drawBadges = () => tabs.forEach((x) => {
    if (!x.badge) return;
    const b = app().querySelector(`[data-tab="${x.id}"]`);
    b.querySelector(".badge-dot")?.remove();
    const n = x.badge();
    if (n) b.insertAdjacentHTML("beforeend", `<span class="badge-dot">${n}</span>`);
  });
  unsubCart?.();
  unsubCart = cart.onChange(drawBadges);
  drawBadges();

  function go(id, params) {
    const tab = tabs.find((x) => x.id === id) || tabs[0];
    cleanup();
    history.replaceState(null, "", `#${tab.id}`);
    app().querySelectorAll(".tabbar button").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab.id));
    const view = document.getElementById("view");
    view.innerHTML = "";
    current = { cleanup: tab.screen.render(view, { go, logout, restart: start, params }) };
  }
  go(first.id);
  startAlarms();
}

function cleanup() { if (current?.cleanup) current.cleanup(); current = null; }

export function logout() {
  auth.clear();
  cart.clear();
  history.replaceState(null, "", "#");
  start();
}

export function changeLang(code) { setLang(code); start(); }

matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => applyTheme());
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
start();
