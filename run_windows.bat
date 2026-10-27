@echo off
REM Medora — Windows uchun bir marta bosib ishga tushirish
cd /d %~dp0
if not exist .venv (
  echo Virtual muhit yaratilmoqda...
  python -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
if not exist db.seeded (
  python manage.py seed_demo
  echo ok > db.seeded
)
echo.
echo  Brauzerda oching:  http://127.0.0.1:8000
echo  API hujjatlari:    http://127.0.0.1:8000/api/docs/
echo.
python manage.py runserver
