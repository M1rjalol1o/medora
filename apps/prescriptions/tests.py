import io
import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.catalog.models import Medicine

from . import vision


def png():
    buf = io.BytesIO()
    Image.new("RGB", (2400, 1800), "white").save(buf, "PNG")
    return SimpleUploadedFile("rx.png", buf.getvalue(), content_type="image/png")


AI_JSON = {"raw_text": "Rp: Paracetamoli 500mg\nS. 1 tab x3 posle edy 5 dney\nНурофен 400 2р/д 7 дн",
           "items": [{"name": "Paracetamol", "dose": "500 mg", "times_per_day": 3, "duration_days": 5,
                      "note": "после еды", "confidence": 0.86},
                     {"name": "Нурофен", "dose": "400 mg", "times_per_day": "2", "duration_days": 7, "confidence": 0.7},
                     {"name": "", "dose": "x"}]}


class VisionTests(TestCase):
    def setUp(self):
        Medicine.objects.create(name="Paratsetamol", dosage="500 mg", aliases="paracetamol, парацетамол")
        Medicine.objects.create(name="Ibuprofen", dosage="400 mg", aliases="нурофен, nurofen")
        self.c = APIClient()
        self.c.force_authenticate(get_user_model().objects.create_user("u", password="secret12"))

    @override_settings(GEMINI_API_KEY="test", OCR_PROVIDERS=["gemini", "openrouter", "tesseract"])
    def test_gemini_handwriting_flow(self):
        resp = {"candidates": [{"content": {"parts": [{"text": json.dumps(AI_JSON)}]}}]}
        with mock.patch.object(vision, "_post", return_value=resp) as post:
            r = self.c.post("/api/prescriptions/", {"image": png()}, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        body = post.call_args[0][1]
        self.assertEqual(body["contents"][0]["parts"][1]["inline_data"]["mime_type"], "image/jpeg")
        d = r.json()
        self.assertTrue(d["ocr_engine"].startswith("gemini:"))
        self.assertEqual([(i["name"], i["times_per_day"]) for i in d["items"]], [("Paratsetamol", 3), ("Ibuprofen", 2)])
        self.assertIsNotNone(d["items"][0]["medicine"])

    @override_settings(GEMINI_API_KEY="test", OPENROUTER_API_KEY="k", OCR_PROVIDERS=["gemini", "openrouter"])
    def test_fallback_to_openrouter(self):
        or_resp = {"choices": [{"message": {"content": "```json\n" + json.dumps(AI_JSON) + "\n```"}}]}

        def fake(url, payload, headers):
            if "google" in url:
                raise vision.VisionError("HTTP 429: quota")
            return or_resp
        with mock.patch.object(vision, "_post", side_effect=fake):
            d = self.c.post("/api/prescriptions/", {"image": png()}, format="multipart").json()
        self.assertTrue(d["ocr_engine"].startswith("openrouter:"))
        self.assertEqual(len(d["items"]), 2)
        self.assertIn("429", d["ocr_errors"][0])

    @override_settings(GEMINI_API_KEY="", OPENROUTER_API_KEY="", OCR_PROVIDERS=["gemini", "openrouter"])
    def test_no_keys_manual(self):
        d = self.c.post("/api/prescriptions/", {"image": png()}, format="multipart").json()
        self.assertEqual(d["ocr_engine"], "none")
