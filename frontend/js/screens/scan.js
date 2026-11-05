// AI skaner: retsept rasmini suratga olish → AI qo'lyozmani o'qiydi → Salomatlik sahifasida tekshirish
import { api } from "../api.js";
import { t } from "../i18n.js";
import { esc, icons, toast } from "../ui.js";

export function render(root, { go }) {
  root.classList.add("scanner");
  root.innerHTML = `<header class="topbar" style="background:transparent;color:#fff">
      <div class="row start" style="gap:10px"><button class="icon-btn" id="back" style="background:#142131;color:#fff;box-shadow:none">←</button>
        <div><h1>${t("AI skaner")}</h1><div class="sub" style="color:#8B9BAD">${t("Qo'lyozma retseptni ham o'qiydi")}</div></div></div></header>
    <div class="screen">
      <div class="scan-box" id="box">
        <span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span>
        <div class="ph" id="ph">${icons.camera}<div>${t("Retseptni ramka ichiga joylang")}</div></div>
        <div class="laser"></div>
      </div>
      <div class="chips mt12" style="justify-content:center">
        <span class="chip" style="background:#142131;color:#8B9BAD">💊 ${t("Dori nomi")}</span>
        <span class="chip" style="background:#142131;color:#8B9BAD">⚖️ ${t("Doza")}</span>
        <span class="chip" style="background:#142131;color:#8B9BAD">⏰ ${t("Necha mahal")}</span>
        <span class="chip" style="background:#142131;color:#8B9BAD">📅 ${t("Necha kun")}</span></div>
      <div id="status" class="mt16"></div>
      <label class="btn mt16" style="cursor:pointer">${icons.camera} ${t("Suratga olish")}<input type="file" id="cam" accept="image/*" capture="environment" hidden></label>
      <label class="btn ghost mt8" style="cursor:pointer;background:#142131;color:#fff;border-color:#22344A">🖼 ${t("Galereyadan tanlash")}<input type="file" id="gal" accept="image/*" hidden></label>
      <button class="btn ghost mt8" id="manual" style="background:transparent;color:#8B9BAD;border-color:#22344A">✍️ ${t("Matn bilan kiritish")}</button>
      <div class="tiny mt16" style="color:#8B9BAD;text-align:center;line-height:1.5">${t("AI tibbiy maslahat bermaydi — faqat retseptda yozilganini o'qiydi. Noaniq joylarni albatta tekshiring yoki farmatsevtdan so'rang.")}</div>
    </div>`;
  const $ = (s) => root.querySelector(s);
  $("#back").onclick = () => go("health");
  $("#manual").onclick = () => go("health", { upload: true });

  async function upload(f) {
    if (!f) return;
    const url = URL.createObjectURL(f);
    $("#ph").outerHTML = `<img id="ph" src="${url}" alt="">`;
    $("#box").classList.add("busy");
    $("#status").innerHTML = `<div class="card"><div class="row start" style="gap:12px"><div class="spinner" style="margin:0;width:22px;height:22px"></div>
      <div><div class="bold small">${t("Retsept o'qilmoqda...")}</div><div class="tiny" style="color:#8B9BAD">${t("AI dori nomlari va dozalarni ajratyapti")}</div></div></div></div>`;
    const fd = new FormData(); fd.append("image", f);
    try {
      const rx = await api("/prescriptions/", { method: "POST", form: fd });
      $("#box").classList.remove("busy");
      $("#status").innerHTML = `<div class="card"><div class="bold">✅ ${t("{n} ta dori topildi", { n: rx.items.length })}</div>
        <div class="tiny mt8" style="color:#8B9BAD">${esc(rx.items.map((i) => `${i.name} ${i.dose || ""}`).join(" · ") || t("Dori topilmadi. Matnni tahrirlab qayta tahlil qiling."))}</div></div>`;
      setTimeout(() => go("health", { rx }), 900);
    } catch (e) {
      $("#box").classList.remove("busy");
      $("#status").innerHTML = "";
      toast(e.message);
    }
  }
  $("#cam").onchange = (e) => upload(e.target.files[0]);
  $("#gal").onchange = (e) => upload(e.target.files[0]);
  return () => root.classList.remove("scanner");
}
