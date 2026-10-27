"""
Retsept rasmidan matn va dorilarni ajratish.

Tartib (settings.OCR_PROVIDERS): gemini -> openrouter -> tesseract.
Kaliti bor birinchi provayder ishlatiladi; xato bersa keyingisiga o'tiladi.
Natija: {"text", "engine", "items" | None, "errors"}
  items — Vision AI to'g'ridan-to'g'ri ajratgan dorilar (bo'lmasa matn parser bilan tahlil qilinadi).
"""
import logging

from django.conf import settings

from . import vision

log = logging.getLogger(__name__)


def _tesseract(image_file):
    try:
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError:
        return None
    try:
        image_file.seek(0)
        img = ImageOps.exif_transpose(Image.open(image_file)).convert("L")
        if img.width < 1400:
            k = 1400 / img.width
            img = img.resize((1400, int(img.height * k)))
        langs = set(pytesseract.get_languages(config=""))
        lang = "+".join(l for l in ("uzb", "rus", "eng") if l in langs) or "eng"
        return pytesseract.image_to_string(img, lang=lang), f"tesseract:{lang}"
    except Exception:
        return None


def read_prescription(image_file) -> dict:
    errors = []
    b64 = None
    for name in [p.strip() for p in settings.OCR_PROVIDERS if p.strip()]:
        if name in vision.PROVIDERS:
            try:
                b64 = b64 or vision._image_b64(image_file)
                r = vision.PROVIDERS[name](b64)
                model = settings.GEMINI_MODEL if name == "gemini" else settings.OPENROUTER_MODEL
                return {"text": r["raw_text"], "engine": f"{name}:{model}", "items": r["items"], "errors": errors}
            except vision.VisionError as e:
                if str(e) != "no key":
                    log.warning("OCR %s failed: %s", name, e)
                    errors.append(f"{name}: {e}"[:200])
        elif name == "tesseract":
            r = _tesseract(image_file)
            if r and r[0].strip():
                return {"text": r[0], "engine": r[1], "items": None, "errors": errors}
    return {"text": "", "engine": "none", "items": None, "errors": errors}


def extract_text(image_file):
    """Eski interfeys (moslik uchun)."""
    r = read_prescription(image_file)
    return r["text"], r["engine"]
