// Dori ichish budilnigi: vaqti kelganda ekran, ovozli signal, tebranish va OVOZDA aytadi.
// Brauzer/PWA ochiq turganda ishlaydi. Telefon ilovasida (Capacitor) LocalNotifications bilan
// ilova yopiq bo'lsa ham ishlaydi — README'ga qarang.
import { api, auth, store } from "./api.js";
import { currentLang, t } from "./i18n.js";
import { app, esc, toast } from "./ui.js";

let courses = [];
let timer = null, loadTimer = null;
let audioCtx = null, beepTimer = null, speakTimer = null;

const today = () => new Date().toISOString().slice(0, 10);
const hhmm = (d = new Date()) => `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;

// Brauzer ovozni faqat foydalanuvchi bosgandan keyin ruxsat beradi — birinchi bosishda tayyorlab qo'yamiz
document.addEventListener("click", () => {
  try { audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)(); audioCtx.resume(); } catch {}
}, { once: false, passive: true });

export async function reloadCourses() {
  if (auth.user?.role !== "customer") return;
  try { courses = await api("/courses/"); } catch {}
}

export function startAlarms() {
  stopAlarms();
  if (auth.user?.role !== "customer") return;
  reloadCourses();
  loadTimer = setInterval(reloadCourses, 5 * 60 * 1000);
  timer = setInterval(check, 15 * 1000);
  setTimeout(check, 3000);
}
export function stopAlarms() { clearInterval(timer); clearInterval(loadTimer); }

function check() {
  const now = new Date();
  const fired = store.get("apteka.alarms.fired") || {};
  const snoozed = store.get("apteka.alarms.snooze") || {};
  // Kechikib ochilgan bo'lsa ham oxirgi 3 daqiqadagi eslatmani ko'rsatamiz
  for (const c of courses) {
    const takenTimes = (c.taken_today || []).map((x) => x.time);
    for (const time of c.times) {
      const key = `${c.id}|${today()}|${time}`;
      if (fired[key] || takenTimes.includes(time)) continue;
      const [h, m] = time.split(":").map(Number);
      const at = new Date(now); at.setHours(h, m, 0, 0);
      const diff = (now - at) / 60000;
      if (diff >= 0 && diff < 3) return ring(c, time, key);
    }
  }
  for (const [key, until] of Object.entries(snoozed)) {
    if (Date.now() >= until) {
      delete snoozed[key]; store.set("apteka.alarms.snooze", snoozed);
      const [id, , time] = key.split("|");
      const c = courses.find((x) => String(x.id) === id);
      if (c) return ring(c, time, key, true);
    }
  }
}

function speakText(text) {
  if (!("speechSynthesis" in window)) return;
  const lang = currentLang();
  const voices = speechSynthesis.getVoices();
  // O'zbek ovozi kam qurilmada bor: bo'lmasa turkcha (lotin talaffuzi yaqin), keyin standart ovoz
  const pref = { uz: ["uz", "tr"], ru: ["ru"], en: ["en"] }[lang];
  const voice = pref.map((p) => voices.find((v) => v.lang.toLowerCase().startsWith(p))).find(Boolean);
  const u = new SpeechSynthesisUtterance(text);
  if (voice) { u.voice = voice; u.lang = voice.lang; } else u.lang = { uz: "uz-UZ", ru: "ru-RU", en: "en-US" }[lang];
  u.rate = 0.95;
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
}

function beep() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    [0, 0.25, 0.5].forEach((off) => {
      const o = audioCtx.createOscillator(), g = audioCtx.createGain();
      o.type = "sine"; o.frequency.value = 880;
      g.gain.setValueAtTime(0.0001, audioCtx.currentTime + off);
      g.gain.exponentialRampToValueAtTime(0.4, audioCtx.currentTime + off + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + off + 0.2);
      o.connect(g).connect(audioCtx.destination);
      o.start(audioCtx.currentTime + off); o.stop(audioCtx.currentTime + off + 0.22);
    });
  } catch {}
  navigator.vibrate?.([300, 150, 300]);
}

function stopSound() { clearInterval(beepTimer); clearInterval(speakTimer); try { speechSynthesis.cancel(); } catch {} }

export function ring(course, time, key, isSnooze = false) {
  if (document.querySelector(".alarm")) return;
  const fired = store.get("apteka.alarms.fired") || {};
  fired[key] = Date.now();
  store.set("apteka.alarms.fired", fired);

  const name = `${course.medicine_name}${course.dose ? ", " + course.dose : ""}`;
  const phrase = t("Dori ichish vaqti keldi. {name}.", { name }) + (course.note ? " " + course.note : "");
  const el = document.createElement("div");
  el.className = "alarm";
  el.innerHTML = `
    <div class="ring">⏰</div>
    <div style="font-size:20px;font-weight:700;margin-top:6px">${esc(time)}</div>
    <h2>${esc(t("Dori ichish vaqti!"))}</h2>
    <div style="font-size:22px;font-weight:800">${esc(course.medicine_name)}</div>
    <div style="opacity:.9;margin-top:4px">${esc(course.dose)}${course.note ? " · " + esc(course.note) : ""}</div>
    <div style="height:24px"></div>
    <button class="btn" id="al-taken">✓ ${esc(t("Ichdim"))}</button>
    <button class="btn ghost" id="al-snooze">${esc(t("10 daqiqadan keyin eslat"))}</button>
    <button class="btn ghost" id="al-skip" style="border:0;opacity:.8">${esc(t("O'tkazib yuborish"))}</button>`;
  app().appendChild(el);

  beep(); beepTimer = setInterval(beep, 1600);
  setTimeout(() => speakText(phrase), 600);
  let n = 0; speakTimer = setInterval(() => { if (++n <= 3) speakText(phrase); }, 9000);
  if ("Notification" in window && Notification.permission === "granted") {
    try { new Notification(t("Dori ichish vaqti!"), { body: name, icon: "icons/icon-192.png", tag: key }); } catch {}
  }

  const close = () => { stopSound(); el.remove(); };
  const log = async (status) => {
    if (course.id < 0) return;
    try { await api(`/courses/${course.id}/log/`, { method: "POST", body: { time, status } }); await reloadCourses(); window.dispatchEvent(new Event("courses-changed")); }
    catch (e) { toast(e.message); }
  };
  el.querySelector("#al-taken").onclick = () => { close(); log("taken"); toast(t("Barakalla! Belgilandi ✓")); };
  el.querySelector("#al-skip").onclick = () => { close(); log("skipped"); };
  el.querySelector("#al-snooze").onclick = () => {
    close();
    const sn = store.get("apteka.alarms.snooze") || {};
    sn[key] = Date.now() + 10 * 60 * 1000;
    store.set("apteka.alarms.snooze", sn);
    toast(t("10 daqiqadan keyin eslatamiz"));
  };
}

export function testAlarm() {
  ring({ id: -1, medicine_name: t("Sinov: Paratsetamol"), dose: "500 mg", note: "" }, hhmm(), `test|${Date.now()}`);
}
