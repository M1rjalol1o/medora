// Xarita (Leaflet ilova ichida, xarita plitkalari OpenStreetMap dan). Internet bo'lmasa — xarita o'rniga ro'yxat.
let loading = null;
export function loadLeaflet() {
  if (window.L) return Promise.resolve(window.L);
  if (loading) return loading;
  loading = new Promise((resolve, reject) => {
    const css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = "vendor/leaflet/leaflet.css";
    document.head.appendChild(css);
    const s = document.createElement("script");
    s.src = "vendor/leaflet/leaflet.js";
    s.onload = () => resolve(window.L);
    s.onerror = () => { loading = null; reject(new Error("map")); };
    document.head.appendChild(s);
    setTimeout(() => { if (!window.L) { loading = null; reject(new Error("timeout")); } }, 8000);
  });
  return loading;
}

const dot = (L, color, label) => L.divIcon({
  className: "", iconSize: [26, 26], iconAnchor: [13, 13],
  html: `<div style="width:26px;height:26px;border-radius:50%;background:${color};color:#fff;border:3px solid #fff;
    box-shadow:0 2px 6px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;font:700 11px Inter,sans-serif">${label}</div>`,
});

/** points: [{lat,lng,label,color}], driver: {lat,lng} | null */
export async function drawRouteMap(el, points, driver) {
  try {
    const L = await loadLeaflet();
    if (!el.isConnected) return null;
    el.innerHTML = "";
    const map = L.map(el, { zoomControl: false, attributionControl: false });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(map);
    const ll = points.map((p) => [p.lat, p.lng]);
    L.polyline(ll, { color: "#0FA37F", weight: 4, opacity: 0.8, dashArray: "6 8" }).addTo(map);
    points.forEach((p) => L.marker([p.lat, p.lng], { icon: dot(L, p.color || "#0FA37F", p.label || "") }).addTo(map));
    let car = null;
    if (driver?.lat) { car = L.marker([driver.lat, driver.lng], { icon: dot(L, "#111827", "🚕") }).addTo(map); ll.push([driver.lat, driver.lng]); }
    map.fitBounds(ll, { padding: [30, 30] });
    return { map, moveDriver: (lat, lng) => car ? car.setLatLng([lat, lng]) : (car = L.marker([lat, lng], { icon: dot(L, "#111827", "🚕") }).addTo(map)) };
  } catch {
    el.style.display = "none";
    return null;
  }
}
