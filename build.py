"""
Vercel build bosqichi (pyproject.toml -> [tool.vercel.scripts] build).
1) Ma'lumotlar bazasi jadvallarini yaratadi (migrate)
2) Baza bo'sh bo'lsa — demo ma'lumot yuklaydi (keyingi deploylarda ma'lumot saqlanib qoladi)
collectstatic'ni Vercel o'zi bajaradi.
"""
import os
import sys

import django


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if not (os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")):
        print("DATABASE_URL yo'q — migratsiya o'tkazib yuborildi (Neon Postgres'ni ulang)")
        return
    django.setup()
    from django.core.management import call_command
    call_command("migrate", interactive=False, verbosity=1)
    from apps.pharmacies.models import Pharmacy
    if not Pharmacy.objects.exists():
        print("Baza bo'sh — demo ma'lumot yuklanmoqda...")
        call_command("seed_demo", days=int(os.getenv("SEED_DAYS", "21")))
    else:
        print("Baza to'la — demo ma'lumot qayta yuklanmadi")


if __name__ == "__main__":
    sys.exit(main())
