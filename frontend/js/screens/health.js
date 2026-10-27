// Salomatlik: retseptni o'qish (OCR + tahlil) va dori ichish jadvali (budilnik)
import { api } from "../api.js";
import { reloadCourses, testAlarm } from "../alarm.js";
import { t } from "../i18n.js";
import { closeSheet, esc, sheet, toast } from "../ui.js";

const DEFAULT_TIMES = { 1: ["09:00"], 2: ["09:00", "21:00"], 3: ["08:00", "14:00", "20:00"], 4: ["08:00", "12:00", "16:00", "20:00"] };
const state = { tab: "schedule", rx: null };

export function render(root, { params, go }) {
  if (params?.upload) state.tab = "rx";
  root.innerHTML = `<header class="topbar"><div><h1>${t("Salomatlik")}</h1><div class="sub">${t("Retsept va dori ichish vaqtlari")}</div></div></header>
    <div class="screen"><div class="seg" id="seg"><button data-v="schedule">⏰ ${t("Jadval")}</button><button data-v="rx">📄 ${t("Retseptlar")}</button></div>
    <div id="c" class="mt12"></div></div>`;
  const c = root.querySelector("#c");
  const segs = () => root.querySelectorAll("#seg button").forEach((b) => b.classList.toggle("active", b.dataset.v === state.tab));
  root.querySelectorAll("#seg button").forEach((b) => (b.onclick = () => { state.tab = b.dataset.v; state.rx = null; segs(); load(); }));
  segs();

  function load() { return state.tab === "schedule" ? loadSchedule() : state.rx ? drawRx(state.rx) : loadRxList(); }

  // ================= JADVAL =================
  async function loadSchedule() {
    c.innerHTML = `<div class="spinner"></div>`;
    let courses = [];
    try { courses = await api("/courses/"); } catch (e) { c.innerHTML = esc(e.message); return; }
    const now = new Date();
    const nowS = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    const doses = [];
    courses.forEach((k) => k.times.forEach((time) => {
      const log = k.taken_today.find((x) => x.time === time);
      doses.push({ k, time, status: log?.status });
    }));
    doses.sort((a, b) => a.time.localeCompare(b.time));
    const next = doses.find((d) => !d.status && d.time >= nowS);

    c.innerHTML = `
      ${next ? `<div class="card recommended"><div class="tiny muted">${t("Keyingi qabul")}</div>
        <div class="row mt8"><div><div class="bold" style="font-size:24px">${esc(next.time)}</div>
        <div class="small">${esc(next.k.medicine_name)} ${esc(next.k.dose)}</div></div><div style="font-size:34px">⏰</div></div></div>` : ""}
      <div class="section-title">${t("Bugun")}</div>
      <div class="card">${doses.length ? doses.map((d) => `
        <div class="dose ${d.status === "taken" ? "taken" : ""}">
          <div class="time">${esc(d.time)}</div>
          <div style="flex:1;min-width:0"><div class="bold small">${esc(d.k.medicine_name)}</div>
            <div class="tiny muted">${esc(d.k.dose)}${d.k.note ? " · " + esc(d.k.note) : ""}${d.status === "skipped" ? " · " + t("o'tkazib yuborildi") : ""}</div></div>
          <button class="check" data-take="${d.k.id}|${d.time}">${d.status === "taken" ? "✓" : ""}</button>
        </div>`).join("") : `<div class="empty" style="padding:24px">${t("Jadval bo'sh. Retsept yuklang yoki qo'lda qo'shing.")}</div>`}</div>

      <div class="section-title">${t("Dori kurslari")}</div>
      ${courses.map((k) => `
        <div class="card"><div class="row"><div><div class="bold">${esc(k.medicine_name)} <span class="muted small">${esc(k.dose)}</span></div>
          <div class="tiny muted">${esc(k.times.join(" · "))} · ${t("{d} gacha", { d: esc(k.end_date) })}</div></div>
          <button class="btn sm secondary" data-edit="${k.id}">${t("Tahrirlash")}</button></div></div>`).join("")}
      <div class="btn-row"><button class="btn" id="add">+ ${t("Qo'lda qo'shish")}</button><button class="btn secondary" id="test">▶ ${t("Signalni sinash")}</button></div>`;

    c.querySelectorAll("[data-take]").forEach((b) => (b.onclick = async () => {
      const [id, time] = b.dataset.take.split("|");
      const d = doses.find((x) => String(x.k.id) === id && x.time === time);
      try {
        await api(`/courses/${id}/log/`, { method: "POST", body: { time, status: d.status === "taken" ? "skipped" : "taken" } });
        reloadCourses(); loadSchedule();
      } catch (e) { toast(e.message); }
    }));
    c.querySelectorAll("[data-edit]").forEach((b) => (b.onclick = () => editCourse(courses.find((k) => k.id == b.dataset.edit))));
    c.querySelector("#add").onclick = () => editCourse(null);
    c.querySelector("#test").onclick = () => testAlarm();
  }

  function timesEditor(times) {
    return `<div id="times" style="display:flex;flex-wrap:wrap;gap:8px">${times.map((x, i) => `
      <span class="chip" style="padding:4px 6px 4px 4px"><input type="time" value="${esc(x)}" data-i="${i}" style="border:0;background:none;color:inherit;font:700 14px Inter"><button data-rm="${i}" style="border:0;background:none;color:var(--danger);cursor:pointer">✕</button></span>`).join("")}
      <button class="btn sm secondary" id="addT">+ ${t("vaqt")}</button></div>`;
  }

  function editCourse(k) {
    let times = k ? [...k.times] : ["09:00"];
    const sh = sheet(`
      <div class="bold" style="font-size:20px">${k ? t("Kursni tahrirlash") : t("Yangi dori kursi")}</div>
      <label class="lbl">${t("Dori nomi")}</label><input class="input" id="nm" value="${esc(k?.medicine_name || "")}">
      <label class="lbl">${t("Doza")}</label><input class="input" id="ds" value="${esc(k?.dose || "")}" placeholder="500 mg, 1 tabletka">
      ${k ? "" : `<label class="lbl">${t("Necha kun")}</label><input class="input" id="dur" type="number" min="1" value="7">`}
      <label class="lbl">${t("Izoh")}</label><input class="input" id="nt" value="${esc(k?.note || "")}" placeholder="${t("ovqatdan keyin")}">
      <label class="lbl">${t("Qabul vaqtlari")}</label><div id="tw"></div>
      <button class="btn mt16" id="save">${t("Saqlash")}</button>
      ${k ? `<button class="btn danger mt8" id="del">${t("Kursni to'xtatish")}</button>` : ""}`);
    const drawT = () => {
      sh.querySelector("#tw").innerHTML = timesEditor(times);
      sh.querySelectorAll("#times input").forEach((inp) => (inp.onchange = () => (times[inp.dataset.i] = inp.value)));
      sh.querySelectorAll("[data-rm]").forEach((b) => (b.onclick = () => { if (times.length > 1) { times.splice(b.dataset.rm, 1); drawT(); } }));
      sh.querySelector("#addT").onclick = () => { times.push("12:00"); drawT(); };
    };
    drawT();
    sh.querySelector("#save").onclick = async () => {
      const body = { medicine_name: sh.querySelector("#nm").value, dose: sh.querySelector("#ds").value, note: sh.querySelector("#nt").value, times };
      try {
        if (k) await api(`/courses/${k.id}/`, { method: "PATCH", body });
        else await api("/courses/", { method: "POST", body: { ...body, duration_days: sh.querySelector("#dur").value } });
        closeSheet(); toast(t("Saqlandi ✓")); reloadCourses(); loadSchedule();
      } catch (e) { toast(e.message); }
    };
    sh.querySelector("#del")?.addEventListener("click", async () => {
      await api(`/courses/${k.id}/`, { method: "DELETE" }); closeSheet(); reloadCourses(); loadSchedule();
    });
  }

  // ================= RETSEPTLAR =================
  async function loadRxList() {
    c.innerHTML = `
      <div class="card" style="text-align:center">
        <div style="font-size:40px">📷</div>
        <div class="bold">${t("Retseptni suratga oling")}</div>
        <div class="small muted mt8">${t("AI dori nomi, doza, necha mahal va necha kun ichishni ajratib beradi. Siz tekshirib tasdiqlaysiz.")}</div>
        <label class="btn mt12" style="cursor:pointer">${t("Rasm yuklash")}<input type="file" id="file" accept="image/*" capture="environment" hidden></label>
        <button class="btn secondary mt8" id="manual">✍️ ${t("Matn bilan kiritish")}</button>
      </div>
      <div class="hint tiny">${t("AI tibbiy maslahat bermaydi — faqat retseptda yozilganini o'qiydi. Noaniq joylarni albatta tekshiring yoki farmatsevtdan so'rang.")}</div>
      <div class="section-title">${t("Mening retseptlarim")}</div><div id="list"><div class="spinner"></div></div>`;
    c.querySelector("#file").onchange = async (e) => {
      const f = e.target.files[0]; if (!f) return;
      const fd = new FormData(); fd.append("image", f);
      c.querySelector("#list").innerHTML = `<div class="spinner"></div><div class="small muted" style="text-align:center">${t("Retsept o'qilmoqda...")}</div>`;
      try { state.rx = await api("/prescriptions/", { method: "POST", form: fd }); drawRx(state.rx); }
      catch (err) { toast(err.message); loadRxList(); }
    };
    c.querySelector("#manual").onclick = () => {
      const sh = sheet(`<div class="bold" style="font-size:20px">${t("Retsept matni")}</div>
        <div class="tiny muted mt8">${t("Har bir dori alohida qatorda. Masalan:")}<br><i>Paratsetamol 500 mg kuniga 3 mahal 5 kun</i></div>
        <textarea class="input mt12" id="tx"></textarea><button class="btn mt12" id="go">${t("Tahlil qilish")}</button>`);
      sh.querySelector("#go").onclick = async () => {
        const fd = new FormData(); fd.append("text", sh.querySelector("#tx").value);
        try { state.rx = await api("/prescriptions/", { method: "POST", form: fd }); closeSheet(); drawRx(state.rx); }
        catch (err) { toast(err.message); }
      };
    };
    try {
      const list = await api("/prescriptions/");
      c.querySelector("#list").innerHTML = list.map((r) => `
        <div class="card" data-rx="${r.id}" style="cursor:pointer"><div class="row"><b>${t("Retsept")} #${r.id}</b><span class="chip ${r.status === "confirmed" ? "ok" : ""}">${r.items.length} ${t("dori")}</span></div>
        <div class="tiny muted mt8">${esc(r.items.map((i) => i.name).join(", ") || r.raw_text.slice(0, 60))}</div></div>`).join("") || `<div class="small muted">${t("Hali retsept yo'q")}</div>`;
      c.querySelectorAll("[data-rx]").forEach((el) => (el.onclick = () => { state.rx = list.find((r) => r.id == el.dataset.rx); drawRx(state.rx); }));
    } catch {}
  }

  function drawRx(rx) {
    const items = rx.items.map((i) => ({ ...i, times: DEFAULT_TIMES[i.times_per_day] || ["09:00"] }));
    c.innerHTML = `
      <button class="btn secondary sm" id="back">← ${t("Orqaga")}</button>
      ${rx.image ? `<img src="${esc(rx.image)}" alt="" style="width:100%;max-height:220px;object-fit:contain;border-radius:14px;margin-top:12px;background:var(--surface-2)">` : ""}
      ${rx.ocr_engine === "none" && rx.image ? `<div class="hint urgent mt12">${t("Avtomatik o'qish bu serverda o'rnatilmagan yoki rasm o'qilmadi. Matnni pastga yozing — tahlil qilamiz.")}</div>` : ""}
      ${/^(gemini|openrouter)/.test(rx.ocr_engine || "") ? `<div class="hint mt12">🤖 ${t("AI qo'lyozmani o'qidi. Har bir dorini rasm bilan solishtirib tekshiring.")} <span class="tiny muted">(${esc(rx.ocr_engine)})</span></div>` : ""}
      ${(rx.ocr_errors || []).length ? `<div class="tiny muted mt8">⚠ ${esc(rx.ocr_errors.join(" · "))}</div>` : ""}
      <label class="lbl">${t("Retsept matni")}</label>
      <textarea class="input" id="raw">${esc(rx.raw_text)}</textarea>
      <button class="btn secondary sm mt8" id="reparse">↻ ${t("Qayta tahlil qilish")}</button>
      <div class="section-title">${t("Topilgan dorilar")} (${items.length})</div>
      <div id="items">${items.map((i, n) => `
        <div class="card" data-n="${n}">
          <div class="row"><input class="input" data-f="name" value="${esc(i.name)}" style="padding:10px 12px;font-weight:700">
            <span class="chip ${i.confidence >= 0.8 ? "ok" : i.confidence >= 0.6 ? "warn" : "danger"}" title="${t("Ishonchlilik")}">${Math.round(i.confidence * 100)}%</span></div>
          <div class="btn-row mt8">
            <input class="input" data-f="dose" value="${esc(i.dose)}" placeholder="${t("Doza")}" style="padding:10px 12px;flex:1;min-width:0">
            <select class="input" data-f="times_per_day" style="padding:10px 8px;flex:1.5;min-width:0;font-size:14px">${[1, 2, 3, 4].map((x) => `<option value="${x}" ${x === i.times_per_day ? "selected" : ""}>${t("kuniga {n} mahal", { n: x })}</option>`).join("")}</select>
          </div>
          <div class="btn-row mt8"><input class="input" type="number" min="1" data-f="duration_days" value="${i.duration_days}" style="padding:10px 12px"><span class="small muted" style="align-self:center">${t("kun")}</span>
            <button class="btn sm danger" data-rm="${n}">✕</button></div>
          <div class="tiny muted mt8">⏰ <span data-times>${i.times.join(" · ")}</span>${i.note ? " · " + esc(i.note) : ""}</div>
          ${i.confidence < 0.7 ? `<div class="tiny mt8" style="color:var(--warn)">⚠ ${t("Noaniq — tekshiring yoki farmatsevtdan so'rang")}</div>` : ""}
        </div>`).join("") || `<div class="small muted">${t("Dori topilmadi. Matnni tahrirlab qayta tahlil qiling.")}</div>`}</div>
      ${items.some((i) => i.medicine) ? `<button class="btn secondary" id="findAll">🔍 ${t("Retseptdagi dorilarni dorixonalardan qidirish")}</button><div style="height:8px"></div>` : ""}
      ${items.length ? `<button class="btn" id="confirm">⏰ ${t("Jadvalga qo'shish va eslatmalarni yoqish")}</button>` : ""}`;
    c.querySelector("#findAll")?.addEventListener("click", () => go("search", {
      basket: items.filter((i) => i.medicine).map((i) => ({ medicine: { ...i.medicine }, quantity: 1 })) }));

    c.querySelector("#back").onclick = () => { state.rx = null; loadRxList(); };
    c.querySelector("#reparse").onclick = async () => {
      try { state.rx = await api(`/prescriptions/${rx.id}/`, { method: "PATCH", body: { text: c.querySelector("#raw").value } }); drawRx(state.rx); }
      catch (e) { toast(e.message); }
    };
    c.querySelectorAll("[data-n]").forEach((card) => {
      const it = items[card.dataset.n];
      card.querySelectorAll("[data-f]").forEach((inp) => (inp.onchange = () => {
        it[inp.dataset.f] = inp.type === "number" || inp.tagName === "SELECT" ? Number(inp.value) : inp.value;
        if (inp.dataset.f === "times_per_day") { it.times = DEFAULT_TIMES[it.times_per_day]; card.querySelector("[data-times]").textContent = it.times.join(" · "); }
      }));
    });
    c.querySelectorAll("[data-rm]").forEach((b) => (b.onclick = () => { rx.items.splice(Number(b.dataset.rm), 1); drawRx(rx); }));
    c.querySelector("#confirm")?.addEventListener("click", async () => {
      try {
        await api(`/prescriptions/${rx.id}/confirm/`, { method: "POST", body: { items } });
        if ("Notification" in window && Notification.permission === "default") Notification.requestPermission();
        toast(t("Jadvalga qo'shildi ✓ Vaqti kelganda eslatamiz"));
        state.rx = null; state.tab = "schedule"; segs(); reloadCourses(); loadSchedule();
      } catch (e) { toast(e.message); }
    });
  }

  load();
  const onChange = () => state.tab === "schedule" && loadSchedule();
  window.addEventListener("courses-changed", onChange);
  return () => window.removeEventListener("courses-changed", onChange);
}
