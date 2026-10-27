"""
Qo'lyozma retseptni o'qish — bepul Vision AI orqali.

  * Google Gemini (AI Studio bepul kaliti) — qo'lyozmani yaxshi o'qiydi, o'zbek/rus/lotin.
  * OpenRouter bepul modellari (masalan Gemma) — zaxira variant.

DIQQAT: bepul tarifda Google yuborilgan ma'lumotdan o'z mahsulotlarini yaxshilash uchun
foydalanishi mumkin. Sinov uchun — faqat roziligi bor odamning retsepti bilan. Haqiqiy
mijozlar uchun pullik tarif (ma'lumot o'qitishga ishlatilmaydi) yoki o'z serverdagi model kerak.

AI tibbiy qaror bermaydi: faqat yozilganini o'qiydi. Natija foydalanuvchiga tasdiqlash uchun ko'rsatiladi.
"""
import base64
import io
import json
import re
import urllib.error
import urllib.request

from django.conf import settings

PROMPT = """You are reading a photo of a medical prescription from Uzbekistan. It may be HANDWRITTEN, in Uzbek (Latin or Cyrillic), Russian or Latin medical abbreviations.

Task: transcribe what is written and extract each prescribed medicine. Do NOT invent anything and do NOT give medical advice.
Common abbreviations: "Rp." recipe, "tab." tablet, "caps." capsule, "x3 / 3 р/д / 3 раза" = 3 times a day, "№10" quantity, "d.t.d." , "S." signa (instructions), "до еды / ovqatdan oldin" before meals, "после еды / ovqatdan keyin" after meals.

Return ONLY valid JSON, no markdown:
{
  "raw_text": "<line-by-line transcription, keep original language>",
  "items": [
    {"name": "<medicine name as written, corrected spelling if obvious>",
     "dose": "<e.g. 500 mg or empty>",
     "times_per_day": <integer 1-6, 1 if unknown>,
     "duration_days": <integer, 5 if unknown>,
     "note": "<e.g. after meals, or empty>",
     "confidence": <0.0-1.0 how sure you are you read this item correctly>}
  ]
}
If the image is not a prescription or unreadable, return {"raw_text": "", "items": []}."""


class VisionError(Exception):
    pass


def _image_b64(fileobj, max_side=1600):
    from PIL import Image, ImageOps
    fileobj.seek(0)
    img = ImageOps.exif_transpose(Image.open(fileobj)).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def _post(url, payload, headers):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=settings.OCR_TIMEOUT_SECONDS) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise VisionError(f"HTTP {e.code}: {e.read()[:300]!r}")
    except Exception as e:                       # tarmoq xatosi, timeout
        raise VisionError(str(e))


def _parse_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)          # ```json ... ``` bo'lsa ham
    if not m:
        raise VisionError("no json")
    data = json.loads(m.group(0))
    items = []
    for it in data.get("items") or []:
        name = str(it.get("name") or "").strip()
        if not name:
            continue
        def num(v, default, lo, hi):
            try:
                return max(lo, min(hi, int(float(v))))
            except (TypeError, ValueError):
                return default
        try:
            conf = max(0.0, min(1.0, float(it.get("confidence", 0.6))))
        except (TypeError, ValueError):
            conf = 0.6
        items.append({"name": name[:200], "dose": str(it.get("dose") or "")[:60],
                      "times_per_day": num(it.get("times_per_day"), 1, 1, 6),
                      "duration_days": num(it.get("duration_days"), 5, 1, 365),
                      "note": str(it.get("note") or "")[:200], "confidence": round(conf, 2)})
    return {"raw_text": str(data.get("raw_text") or "")[:5000], "items": items}


def gemini(image_b64: str) -> dict:
    key = settings.GEMINI_API_KEY
    if not key:
        raise VisionError("no key")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": PROMPT}, {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    r = _post(url, payload, {"x-goog-api-key": key})
    try:
        text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError):
        raise VisionError(f"bad response: {str(r)[:200]}")
    return _parse_json(text)


def openrouter(image_b64: str) -> dict:
    key = settings.OPENROUTER_API_KEY
    if not key:
        raise VisionError("no key")
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
        ]}],
    }
    r = _post("https://openrouter.ai/api/v1/chat/completions", payload,
              {"Authorization": f"Bearer {key}", "X-Title": "Medora"})
    try:
        text = r["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise VisionError(f"bad response: {str(r)[:200]}")
    return _parse_json(text if isinstance(text, str) else json.dumps(text))


PROVIDERS = {"gemini": gemini, "openrouter": openrouter}
