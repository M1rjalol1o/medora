"""
Retsept matnini strukturaga aylantirish: dori nomi, doza, kuniga necha mahal, necha kun.
AI tibbiy qaror bermaydi — faqat yozilganini ajratadi, foydalanuvchi tasdiqlaydi.

Tushunadigan yozuvlar (o'zbek / rus / ingliz):
  "Paratsetamol 500 mg kuniga 3 mahal 5 kun"
  "Ибупрофен 400мг 2 раза в день 7 дней"
  "Amoxicillin 500mg 3 times a day for 7 days"
  "Drotaverin 40 mg 1 tab x 3, 5 kun"
"""
import re

from apps.catalog.models import Medicine
from apps.catalog.utils import normalize

DOSE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mg|мг|mcg|мкг|g|г|ml|мл|%|me|ед)\b", re.I)
TIMES = [
    re.compile(r"kuniga\s*(\d)\s*(?:mahal|marta|maxal|marotaba)", re.I),
    re.compile(r"(\d)\s*(?:mahal|marta|maxal)\s*(?:kuniga)?", re.I),
    re.compile(r"(\d)\s*(?:раз[а]?)\s*(?:в\s*(?:день|сутки))?", re.I),
    re.compile(r"(\d)\s*р\s*/\s*д", re.I),
    re.compile(r"(\d)\s*times?\s*(?:a|per)\s*day", re.I),
    re.compile(r"[x×х]\s*(\d)\b", re.I),
]
WORD_TIMES = {"bir": 1, "ikki": 2, "uch": 3, "to'rt": 4, "один": 1, "два": 2, "три": 3, "once": 1, "twice": 2}
DURATION = re.compile(r"(\d{1,2})\s*(?:kun|кун|дн(?:ей|я)?|сут|days?)\b", re.I)
WEEKS = re.compile(r"(\d)\s*(?:hafta|недел[иья]|weeks?)\b", re.I)
NOTE = re.compile(r"(ovqatdan\s*(?:oldin|keyin)|до\s*еды|после\s*еды|before\s*meals?|after\s*meals?|och\s*qoringa|натощак)", re.I)


def _catalog():
    items = []
    for m in Medicine.objects.all():
        keys = {normalize(m.name), normalize(m.inn)}
        keys |= {normalize(a) for a in m.aliases.split(",") if a.strip()}
        items.append((m, {k for k in keys if len(k) >= 4}))
    return items


def _find_medicine(line_n, catalog):
    best, best_len = None, 0
    for m, keys in catalog:
        for k in keys:
            # nomning birinchi 5 harfi ham yetarli (OCR xatolariga chidamli)
            if k in line_n or (len(k) >= 7 and k[:6] in line_n):
                if len(k) > best_len:
                    best, best_len = m, len(k)
    return best


def parse(text: str) -> list:
    catalog = _catalog()
    results = []
    for raw in re.split(r"[\n;]+", text or ""):
        line = re.sub(r"^\s*(?:rp\.?|\d{1,2}[.)])\s*", "", raw, flags=re.I).strip(" .,-•*\t")
        if len(line) < 3:
            continue
        ln = normalize(line)
        med = _find_medicine(ln, catalog)
        dose_m = DOSE.search(line)
        times = None
        for rx in TIMES:
            m = rx.search(line)
            if m and 1 <= int(m.group(1)) <= 6:
                times = int(m.group(1))
                break
        if times is None:
            for w, n in WORD_TIMES.items():
                if re.search(rf"\b{re.escape(w)}\b", ln):
                    times = n
                    break
        dur = DURATION.search(line)
        weeks = WEEKS.search(line)
        if not med and not (dose_m and re.match(r"[A-Za-zА-Яа-яЁёʻ'‘]{4,}", line)):
            continue
        name = str(med.name) if med else re.match(r"[A-Za-zА-Яа-яЁёʻ'‘\-]+(?:\s+[A-Za-zА-Яа-яЁё\-]+)?", line).group(0)
        confidence = 0.4 + (0.3 if med else 0) + (0.1 if dose_m else 0) + (0.1 if times else 0) + (0.1 if dur else 0)
        results.append({
            "medicine_id": med.id if med else None,
            "name": name,
            "dose": f"{dose_m.group(1)} {dose_m.group(2)}" if dose_m else (med.dosage if med else ""),
            "times_per_day": times or 1,
            "duration_days": int(dur.group(1)) if dur else (int(weeks.group(1)) * 7 if weeks else 5),
            "note": NOTE.search(line).group(1) if NOTE.search(line) else "",
            "confidence": round(min(confidence, 1.0), 2),
            "source": line[:200],
        })
    return results


DEFAULT_TIMES = {1: ["09:00"], 2: ["09:00", "21:00"], 3: ["08:00", "14:00", "20:00"],
                 4: ["08:00", "12:00", "16:00", "20:00"], 5: ["07:00", "11:00", "15:00", "19:00", "23:00"],
                 6: ["06:00", "10:00", "14:00", "18:00", "22:00", "02:00"]}


def default_times(n: int) -> list:
    return DEFAULT_TIMES.get(max(1, min(6, n)), ["09:00"])
