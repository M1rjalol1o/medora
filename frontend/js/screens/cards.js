// Karta qo'shish oqimi: raqam + muddat -> SMS kod -> saqlangan karta (faqat token va oxirgi 4 raqam)
import { api } from "../api.js";
import { t } from "../i18n.js";
import { closeSheet, esc, sheet, toast } from "../ui.js";

export function cardVisual(c) {
  return `<div class="card-visual ${esc(c.brand.toLowerCase())}"><div class="row"><b>${esc(c.brand)}</b><span class="tiny">${esc(c.expiry)}</span></div>
    <div style="font-size:19px;letter-spacing:2px;margin-top:22px;font-weight:600">${esc(c.masked)}</div></div>`;
}

export function addCardFlow() {
  return new Promise((resolve) => {
    const sh = sheet(`
      <div class="bold" style="font-size:20px">${t("Karta qo'shish")}</div>
      <div class="small muted mt8">${t("Uzcard, Humo, Visa, Mastercard. Karta raqami ilovada saqlanmaydi.")}</div>
      <label class="lbl">${t("Karta raqami")}</label>
      <input class="input" id="num" inputmode="numeric" autocomplete="cc-number" placeholder="8600 0000 0000 0000" maxlength="23">
      <label class="lbl">${t("Amal qilish muddati")}</label>
      <input class="input" id="exp" inputmode="numeric" autocomplete="cc-exp" placeholder="MM/YY" maxlength="5">
      <div class="hint mt12 tiny">${t("Sinov rejimi: 8600 0000 0000 0007 kartasi bilan sinab ko'ring. SMS kod ekranda ko'rsatiladi.")}</div>
      <button class="btn mt16" id="next">${t("Davom etish")}</button>`);
    const num = sh.querySelector("#num"), exp = sh.querySelector("#exp");
    num.oninput = () => { num.value = num.value.replace(/\D/g, "").slice(0, 19).replace(/(\d{4})(?=\d)/g, "$1 "); };
    exp.oninput = () => { let v = exp.value.replace(/\D/g, "").slice(0, 4); if (v.length > 2) v = v.slice(0, 2) + "/" + v.slice(2); exp.value = v; };
    sh.querySelector("#next").onclick = async (e) => {
      e.target.disabled = true;
      try {
        const r = await api("/payments/cards/", { method: "POST", body: { number: num.value, expiry: exp.value } });
        otpStep(r, resolve);
      } catch (err) { toast(err.message); e.target.disabled = false; }
    };
  });
}

function otpStep(r, resolve) {
  const sh = sheet(`
    <div class="bold" style="font-size:20px">${t("SMS kodni kiriting")}</div>
    <div class="small muted mt8">${t("Kod {phone} raqamiga yuborildi", { phone: esc(r.phone_hint) })}</div>
    ${r.sandbox_code ? `<div class="hint mt12">${t("Sinov rejimi — SMS kod")}: <b style="letter-spacing:3px">${esc(r.sandbox_code)}</b></div>` : ""}
    <input class="input mt16" id="code" inputmode="numeric" maxlength="6" autocomplete="one-time-code"
      style="font-size:28px;text-align:center;letter-spacing:10px">
    <button class="btn mt16" id="ok">${t("Tasdiqlash")}</button>`);
  sh.querySelector("#code").focus();
  sh.querySelector("#ok").onclick = async (e) => {
    e.target.disabled = true;
    try {
      const card = await api("/payments/cards/verify/", { method: "POST", body: { session: r.session, code: sh.querySelector("#code").value } });
      closeSheet(); toast(t("Karta qo'shildi ✓")); resolve(card);
    } catch (err) { toast(err.message); e.target.disabled = false; }
  };
}
