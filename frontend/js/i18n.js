// 3 til: o'zbek (asosiy), rus, ingliz. Matnlar o'zbekcha yoziladi, tarjima translations.js da.
import { RU, EN } from "./translations.js";

const KEY = "apteka.lang";
export const LANGS = [
  { code: "uz", label: "O'zbek" },
  { code: "ru", label: "Русский" },
  { code: "en", label: "English" },
];

export function getLang() {
  // Standart til — o'zbekcha. Foydalanuvchi tanlasa, shu eslab qolinadi.
  try { return localStorage.getItem(KEY) || "uz"; }
  catch { return "uz"; }
}
let lang = ["uz", "ru", "en"].includes(getLang()) ? getLang() : "uz";

export function setLang(code) {
  lang = code;
  try { localStorage.setItem(KEY, code); } catch {}
  document.documentElement.lang = code;
}
export const currentLang = () => lang;

export function t(text, vars) {
  let out = lang === "ru" ? RU[text] ?? text : lang === "en" ? EN[text] ?? text : text;
  if (vars) for (const [k, v] of Object.entries(vars)) out = out.split(`{${k}}`).join(v);
  return out;
}

// Holat kodlari -> matn
const STATUS = {
  pending: "Kutilmoqda", confirmed: "Qabul qilindi", completed: "Yakunlandi", cancelled: "Bekor qilindi",
  expired: "Muddati o'tdi", awaiting_payment: "To'lov kutilmoqda", preparing: "Tayyorlanmoqda", ready: "Tayyor",
  delivering: "Yo'lda", new: "Yangi", accepted: "Qabul qilindi", picked_up: "Haydovchi oldi", issued: "Berildi",
  rejected: "Rad etildi", searching: "Haydovchi qidirilmoqda", assigned: "Haydovchi biriktirildi",
  picking: "Dorixonalardan olinmoqda", delivered: "Yetkazildi", paid: "To'landi", cash_pending: "Naqd — yetkazishda",
  failed: "Xato", refunded: "Qaytarildi",
  customer: "Mijoz", pharmacy: "Dorixona", driver: "Haydovchi", taxipark: "Taksopark", admin: "Administrator",
  card: "Karta", cash: "Naqd", delivery: "Yetkazib berish", pickup: "O'zim olib ketaman",
};
export const st = (code) => t(STATUS[code] || code);
