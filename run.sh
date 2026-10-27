#!/usr/bin/env bash
# Medora — Linux/macOS uchun ishga tushirish
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
[ -f db.seeded ] || { python manage.py seed_demo && touch db.seeded; }
echo "Brauzerda oching: http://127.0.0.1:8000   ·   API: http://127.0.0.1:8000/api/docs/"
python manage.py runserver
