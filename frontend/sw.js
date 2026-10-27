// Service worker: ilova qobig'ini keshlaydi (tez ochilish, oflayn ekran).
// API so'rovlari keshlanmaydi — qoldiq har doim yangi bo'lishi kerak.
const CACHE = "medora-shell-v4";
const SHELL = ["/", "/css/app.css", "/js/app.js", "/js/api.js", "/js/config.js", "/js/ui.js", "/js/i18n.js",
  "/js/translations.js", "/js/cart.js", "/js/alarm.js", "/js/map.js",
  "/js/screens/login.js", "/js/screens/search.js", "/js/screens/cart.js", "/js/screens/orders.js",
  "/js/screens/health.js", "/js/screens/profile.js", "/js/screens/cards.js", "/js/screens/panel.js",
  "/js/screens/driver.js", "/js/screens/park.js", "/js/screens/admin.js", "/manifest.webmanifest"];

self.addEventListener("install", (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))));
self.addEventListener("activate", (e) => e.waitUntil(
  caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))));
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/") || e.request.method !== "GET") return;
  e.respondWith(fetch(e.request).then((r) => {
    const copy = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); return r;
  }).catch(() => caches.match(e.request)));
});
