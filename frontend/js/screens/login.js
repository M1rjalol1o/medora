import { api, auth, login } from "../api.js";
import { LANGS, currentLang, setLang, t } from "../i18n.js";
import { esc, icons, toast } from "../ui.js";

const DEMO = [
  ["demo", "👤", "Mijoz"], ["dorixona1", "🏥", "Dorixona"], ["driver1", "🚕", "Haydovchi"],
  ["park1", "🏢", "Taksopark"], ["admin", "🛡", "Admin"],
];

export function render(root, { onLogin }) {
  let mode = "login";
  const draw = () => {
    root.innerHTML = `
    <div class="screen" style="padding-bottom:30px">
      <div class="login-hero">
        <div class="row">
          <div class="row start" style="gap:12px"><div class="logo">${icons.pill}</div>
            <div style="font-size:26px;font-weight:800;letter-spacing:-.5px">Malhamix</div></div>
          <div class="lang-switch">${LANGS.map((l) => `<button data-lang="${l.code}" class="${l.code === currentLang() ? "active" : ""}" style="background:rgba(255,255,255,${l.code === currentLang() ? ".95" : ".15"});color:${l.code === currentLang() ? "#0A7C92" : "#fff"};border:0">${l.code.toUpperCase()}</button>`).join("")}</div>
        </div>
        <h1>${t("Dori toping — kafolat bilan")}</h1>
        <p>${t("Yetib borguningizcha dori qoladimi? Ilova oldindan aytadi.")}</p>
        <div class="chips mt16"><span class="chip" style="background:rgba(255,255,255,.18);color:#fff">🤖 AI</span>
          <span class="chip" style="background:rgba(255,255,255,.18);color:#fff">🚕 ${t("Yetkazish")}</span>
          <span class="chip" style="background:rgba(255,255,255,.18);color:#fff">⏰ ${t("Budilnik")}</span></div>
      </div>
      <form id="f" class="mt16">
        ${mode === "register" ? `<label class="lbl">${t("Ismingiz")}</label><input class="input" name="first_name" required>
          <label class="lbl">${t("Telefon")}</label><input class="input" name="phone" placeholder="+998" inputmode="tel">` : ""}
        <label class="lbl">${t("Login")}</label><input class="input" name="username" autocomplete="username" required>
        <label class="lbl">${t("Parol")}</label><input class="input" name="password" type="password" autocomplete="current-password" required>
        <button class="btn mt16" type="submit">${mode === "login" ? t("Kirish") : t("Ro'yxatdan o'tish")}</button>
      </form>
      <button class="btn secondary mt8" id="switch">${mode === "login" ? t("Hisobingiz yo'qmi? Ro'yxatdan o'ting") : t("Hisobim bor — kirish")}</button>
      <div class="section-title">${t("Demo kirish")}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        ${DEMO.map(([u, e, l]) => `<button class="btn secondary" data-demo="${u}">${e} ${t(l)}</button>`).join("")}
      </div>
      <div class="tiny muted mt8" style="text-align:center">${t("Parol: demo1234 (admin: admin1234)")}</div>
    </div>`;

    root.querySelectorAll("[data-lang]").forEach((b) => (b.onclick = () => { setLang(b.dataset.lang); draw(); }));
    root.querySelector("#switch").onclick = () => { mode = mode === "login" ? "register" : "login"; draw(); };
    root.querySelectorAll("[data-demo]").forEach((b) => (b.onclick = () =>
      doLogin(b.dataset.demo, b.dataset.demo === "admin" ? "admin1234" : "demo1234")));
    root.querySelector("#f").onsubmit = async (e) => {
      e.preventDefault();
      const d = Object.fromEntries(new FormData(e.target));
      if (mode === "login") return doLogin(d.username, d.password);
      try {
        const res = await api("/auth/register/", { method: "POST", body: { ...d, language: currentLang() }, retry: false });
        auth.save({ access: res.access, refresh: res.refresh }, res.user);
        onLogin();
      } catch (err) { toast(err.message); }
    };
  };

  async function doLogin(u, p) {
    try { await login(u, p); onLogin(); }
    catch (err) { toast(err.status === 401 ? t("Login yoki parol noto'g'ri") : err.status === 0 ? t("Server bilan aloqa yo'q") : esc(err.message)); }
  }
  draw();
}
