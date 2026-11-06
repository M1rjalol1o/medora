#!/bin/sh
# Konteyner ishga tushganda: bazani kutish -> migratsiya -> baza bo'sh bo'lsa demo ma'lumot
set -e

python - <<'PY'
import os, time
import psycopg
url = os.getenv("DATABASE_URL")
if url:
    for i in range(30):
        try:
            psycopg.connect(url).close(); break
        except Exception:
            print("Postgres kutilmoqda..."); time.sleep(2)
PY

python manage.py migrate --noinput
python - <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.core.management import call_command
from apps.pharmacies.models import Pharmacy
if not Pharmacy.objects.exists():
    print("Baza bo'sh — demo ma'lumot yuklanmoqda...")
    call_command("seed_demo", days=int(os.getenv("SEED_DAYS", "21")))
PY

exec "$@"
