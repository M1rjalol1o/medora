"""
Medora — Django sozlamalari.

Muhit o'zgaruvchilari (ixtiyoriy):
  DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS
  POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT
Agar POSTGRES_DB berilmasa, SQLite ishlatiladi (tez boshlash uchun).
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# backend/.env faylidan kalitlarni o'qish (GEMINI_API_KEY va h.k.). Fayl git'ga qo'shilmaydi.
_env = BASE_DIR / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.strip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
FRONTEND_DIR = BASE_DIR / "frontend"

ON_VERCEL = os.getenv("VERCEL") == "1"

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if ON_VERCEL:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("Vercel'da DJANGO_SECRET_KEY muhit o'zgaruvchisini o'rnating")
    SECRET_KEY = "dev-only-secret-change-me-in-production-0123456789"
DEBUG = os.getenv("DJANGO_DEBUG", "0" if ON_VERCEL else "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")
CSRF_TRUSTED_ORIGINS = ["https://*.vercel.app"] + [o for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Frontend (mobil ilova qobig'i) shu server orqali beriladi
SERVE_FRONTEND = os.getenv("SERVE_FRONTEND", "1") == "1"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    # loyiha
    "apps.accounts",
    "apps.catalog",
    "apps.pharmacies",
    "apps.reservations",
    "apps.search",
    "apps.panel",
    "apps.orders",
    "apps.delivery",
    "apps.payments",
    "apps.prescriptions",
    "apps.adminpanel",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

_db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
if _db_url:
    # Vercel + Neon: postgresql://user:pass@host/db?sslmode=require
    import urllib.parse as _up
    _u = _up.urlparse(_db_url)
    _q = dict(_up.parse_qsl(_u.query))
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _u.path.lstrip("/"),
            "USER": _up.unquote(_u.username or ""),
            "PASSWORD": _up.unquote(_u.password or ""),
            "HOST": _u.hostname,
            "PORT": _u.port or 5432,
            "OPTIONS": {"sslmode": _q.get("sslmode", "require")},
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": True,
        }
    }
elif os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
# Vercel'da fayl tizimi faqat /tmp da yoziladi (vaqtinchalik). Doimiy saqlash uchun keyin Vercel Blob/S3.
MEDIA_ROOT = Path("/tmp/media") if ON_VERCEL else BASE_DIR / "media"
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- API ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Medora API",
    "DESCRIPTION": "Medora: dori qidiruvi va qolish ehtimoli bashorati, bir nechta dorini birga qidirish, bron, "
                   "savat va bitta to'lov, taksi orqali yetkazish, retsept o'qish, dori budilnigi, dorixona/taksopark/admin panellari. "
                   "Demo: demo/demo1234 (mijoz), dorixona1, driver1, park1 (parol demo1234). Avtorizatsiya: POST /api/auth/login/ -> Bearer token.",
    "VERSION": "1.0.0",
}

# Mobil ilova (Capacitor / React Native / Flutter) boshqa origin'dan so'rov yuboradi
CORS_ALLOW_ALL_ORIGINS = True          # JWT (cookie emas) — mobil ilova istalgan joydan ulanadi

# --- Biznes sozlamalari ---
# Bron muddati = mijozning dorixonagacha PIYODA yo'l vaqti + shu qo'shimcha daqiqa
RESERVATION_EXTRA_MINUTES = 20
RESERVATION_MAX_MINUTES = 240          # 4 soatdan ortiq ushlab turilmaydi
RESERVATION_HOLD_MINUTES = 20          # lokatsiya noma'lum bo'lsa
ORDER_PAYMENT_TIMEOUT_MINUTES = 15     # karta to'lovi shu vaqtda bo'lmasa buyurtma bekor
EXPIRING_SOON_DAYS = 90                # "muddati yaqin" chegarasi

# Yetkazish narxi (so'm)
DELIVERY_BASE_FEE = 7000
DELIVERY_PER_KM = 2000
DELIVERY_PER_EXTRA_STOP = 3000
PLATFORM_COMMISSION_PERCENT = 10       # yetkazish narxidan platforma ulushi

# To'lov provayderi: "sandbox" (sinov). Haqiqiy: Payme/Click ulanganda o'zgaradi.
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "sandbox")
# --- Retseptni o'qish (qo'lyozma ham) ---
# Tartib bilan sinab ko'riladi: kaliti bor birinchi provayder ishlatiladi.
#   gemini     — Google AI Studio bepul kaliti (https://aistudio.google.com/apikey)
#   openrouter — OpenRouter bepul modellari (https://openrouter.ai/keys)
#   tesseract  — oflayn, faqat bosma matn uchun
OCR_PROVIDERS = os.getenv("OCR_PROVIDERS", "gemini,openrouter,tesseract").split(",")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
OCR_TIMEOUT_SECONDS = 60
PREDICTION_HISTORY_DAYS = 28           # sotuv tezligi necha kunlik tarixdan hisoblanadi
GUARANTEED_PROBABILITY = 0.9           # "kafolatli" deb hisoblanadigan chegara
