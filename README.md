# Medora — dori topish, yetkazish va salomatlik platformasi

Bu platformada quyidagilar bitta ilovada ishlaydi:

- dori qidiruvi va **"yetib borguningizcha dori qoladimi?"** degan AI bashorati;
- savat va **bitta to'lov**: bir nechta dorixonadan olingan dorilar va taksi uchun pul bir marta to'lanadi;
- taksi orqali yetkazish;
- retseptni o'qish;
- **ovozli dori budilnigi**.

Ilova 3 tilda ishlaydi (o'zbek, rus, ingliz) va kunduzgi/tungi mavzuga ega.

## Ishga tushirish (Windows, PyCharm terminali)

```powershell
cd medora
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Keyin brauzerda **http://127.0.0.1:8000** ni oching.

> Ma'lumotlar bazasi tuzilmasi o'zgargan bo'lsa, `db.sqlite3` faylini o'chirib, yuqoridagi buyruqlarni qayta bajaring.

| Rol | Login | Parol | Nima qila oladi |
|---|---|---|---|
| Mijoz | `demo` | `demo1234` | qidiruv, savat, to'lov, kuzatish, bron, retsept, budilnik |
| Dorixona | `dorixona1`…`dorixona12` | `demo1234` | buyurtmalar, bronlar, ombor, muddati yaqin dorilar, retsept tekshirish |
| Haydovchi | `driver1`…`driver6` | `demo1234` | onlayn/oflayn, buyurtma olish, marshrut, naqd pul, daromad |
| Taksopark | `park1`, `park2` | `demo1234` | haydovchilar, dispetcherlik, daromad |
| Admin | `admin` | `admin1234` | **hammasi**: foydalanuvchilar, dorixonalar, buyurtmalar, to'lovlar, bronlar, taksi |

API hujjati: http://127.0.0.1:8000/api/docs/ · Django admin: http://127.0.0.1:8000/admin/ · Testlar: `python manage.py test apps`

## Asosiy qoidalar

**Bron muddati** = mijozning dorixonagacha **piyoda yo'l vaqti + 20 daqiqa**. Eng ko'pi 4 soat. Sozlamasi: `settings.RESERVATION_*`.

**Bitta to'lov.** Mijoz 10 ta dorixonadan dori olsa ham bitta buyurtma va bitta to'lov bo'ladi.

- Buyurtma ichida har bir dorixona uchun alohida sub-buyurtma (`PharmacyOrder`) yaratiladi.
- Taksi bitta marshrut bo'yicha yuradi: dorixona 1 → dorixona 2 → … → mijoz.
- **Karta:** to'lov ilovaning ichida, karta qo'shishda SMS kod so'raladi.
- **Naqd:** pul haydovchiga beriladi (o'zi olib ketsa, dorixonada).

**Karta xavfsizligi.** Karta raqami ilovada **saqlanmaydi**, faqat provayder tokeni va oxirgi 4 raqam saqlanadi. Hozir sinov rejimi (`sandbox`) ishlaydi, SMS kod ekranda ko'rsatiladi. Sinov kartalari:

- `8600 0000 0000 0007` — muvaffaqiyatli to'lov;
- `8600 1111 0009 0002` — "mablag' yetarli emas".

**Haqiqiy to'lov** uchun Payme yoki Click bilan merchant shartnoma tuzish kerak. Keyin `apps/payments/provider.py` faylida `PaymeProvider` yoziladi va `PAYMENT_PROVIDER=payme` qilib qo'yiladi.

**Taksi:**

- To'lanmagan buyurtma haydovchilarga ko'rinmaydi.
- Haydovchi dorini dorixona "Tayyor" degandan keyingina ola oladi.
- Mijozga topshirishda mijozning 4 xonali kodi so'raladi.
- Yetkazish narxi taqsimlanadi: platforma 10%, taksopark o'z ulushi, qolgani haydovchiga.

**Retseptli dori:**

- Retseptli dorini buyurtma qilish uchun retsept biriktirish shart.
- Farmatsevt retseptni tasdiqlamaguncha buyurtmani "Tayyor" qilib bo'lmaydi.

**Muddati yaqin dorilar** (dorixona, Ombor → Muddati yaqin):

- 90 kun ichida muddati tugaydigan dorilar ko'rsatiladi.
- Sotuv tezligiga qarab qancha dona sotilmay qolishi va qancha zarar bo'lishi hisoblanadi.
- Chegirma tavsiya qilinadi. Dorixona chegirma qo'ysa, mijoz uni qidiruvda ko'radi.

**Bir nechta dorini birga qidirish** (shifokor odatda 2–3 ta dori yozadi):

- Qidiruvda har bir dori yonidagi **+** tugmasi uni ro'yxatga qo'shadi, keyin "Hammasini birga qidirish" bosiladi. Retsept sahifasida esa "Retseptdagi dorilarni qidirish" tugmasi bor.
- Tizim dorixonalarning 1, 2 va 3 tadan kombinatsiyalarini hisoblaydi. Har bir dorixonaga yetib borish vaqti marshrut bo'yicha olinadi va **hamma dorilar qolish ehtimoli** chiqariladi.
- Natijada quyidagi variantlar ko'rsatiladi: **Tavsiya**, **Hammasi bir joyda**, **Eng tez**, **Eng ishonchli** va **Eng yaqin dorixona**. Eng yaqin dorixona uchun qaysi dori yo'qligi yoziladi, masalan: "2/3 bor, yo'q: Ibuprofen".
- Tanlangan variantni bir bosishda savatga qo'shish yoki bron qilish mumkin.
- Kod: `apps/search/basket.py`.

**Retsept o'qish (qo'lyozma ham) — bepul:**

1. https://aistudio.google.com/apikey saytiga Google akkaunt bilan kiring va "Create API key" tugmasini bosing (karta so'ralmaydi).
2. `.env.example` faylini `.env` nomi bilan nusxalang va `GEMINI_API_KEY=` qatoriga kalitni yozing.
3. Serverni qayta ishga tushiring. Endi retsept rasmi yuklanganda Gemini qo'lyozmani o'qib, dorilarni ajratib beradi.
4. Zaxira variant: OpenRouter bepul kaliti (`OPENROUTER_API_KEY`). Gemini limiti tugasa, avtomatik shunga o'tiladi.

> ⚠️ Bepul tarifda Google yuborilgan rasmlardan o'z xizmatlarini yaxshilash uchun foydalanishi mumkin. Sinovda faqat roziligi olingan odamning retseptini ishlating. Haqiqiy mijozlar uchun pullik tarif kerak (unda ma'lumot o'qitishga ishlatilmaydi).

**Retsept o'qish (oflayn, ixtiyoriy):**

- Rasm yuklansa, OCR (Tesseract) orqali matn olinadi. Tahlilchi dori nomi, doza, "kuniga necha mahal" va "necha kun" ma'lumotini 3 tilda tushunadi.
- Tesseract o'rnatilmagan bo'lsa, matnni o'zingiz yozasiz, tahlil baribir ishlaydi.
- Tesseract o'rnatish (ixtiyoriy):
  1. https://github.com/UB-Mannheim/tesseract/wiki saytidan dasturni o'rnating (uzb va rus tillarini tanlang).
  2. `pip install pytesseract` buyrug'ini bajaring.
- Qo'lyozma retseptlarni Tesseract yomon o'qiydi. Ular uchun keyinchalik `apps/prescriptions/ocr.py` faylida Vision AI ulanadi.

**Dori budilnigi:**

- Vaqti kelganda to'liq ekran ochiladi, signal chalinadi, telefon tebranadi va eslatma **ovozda aytiladi** (tanlangan tilda).
- Ichilgan, keyinga surilgan (10 daqiqa) va o'tkazib yuborilgan qabullar belgilanadi.
- Brauzer yoki PWA ochiq bo'lishi kerak.
- Ilova **yopiq** bo'lganda ham ishlashi uchun Capacitor ilovada `@capacitor/local-notifications` plaginini ulash kerak (pastga qarang).

## Serverga joylash (Vercel + Neon Postgres)

1. Repozitoriyni Vercel'ga import qiling (Framework: Django avtomatik aniqlanadi).
2. Storage → **Neon Postgres** qo'shing (bepul tarif). `DATABASE_URL` avtomatik qo'shiladi.
3. Environment Variables bo'limiga quyidagilarni qo'shing:
   - `DJANGO_SECRET_KEY` — tasodifiy uzun satr;
   - `ADMIN_PASSWORD` — admin paroli;
   - ixtiyoriy: `GEMINI_API_KEY`.
4. Deploy qiling. Build bosqichida `build.py` jadvallarni yaratadi va baza bo'sh bo'lsa demo ma'lumot yuklaydi.

Cheklov: Vercel'da yuklangan retsept rasmlari vaqtinchalik saqlanadi (`/tmp`). Doimiy saqlash uchun Vercel Blob yoki S3 ulanadi.

## Telefon ilovasi (Android)

```bash
cd frontend
npm init -y && npm i @capacitor/core @capacitor/cli @capacitor/android @capacitor/local-notifications
npx cap add android && npx cap open android
```

`frontend/js/config.js` faylidagi `API_BASE` qatoriga server manzilini yozing.

## Tuzilma

```
apps/
  accounts       rollar: mijoz, dorixona, haydovchi, taksopark, admin; JWT; 3 tilli xabarlar
  catalog        dori katalogi
  pharmacies     dorixona, qoldiq, sotuv tarixi, seed_demo
  search         qidiruv, AI bashorat (Poisson), saralash
  reservations   bron (piyoda + 20 daqiqa)
  orders         buyurtma, dorixona sub-buyurtmalari, marshrut va yetkazish narxi
  payments       karta (token), SMS tasdiqlash, bitta to'lov, provayder abstraksiyasi
  delivery       taksopark, haydovchi, yetkazish, marshrut nuqtalari, daromad taqsimoti
  prescriptions  retsept, OCR, tahlilchi, dori kurslari, qabul jurnali
  panel          dorixona paneli (buyurtmalar, muddati yaqin, chegirma)
  adminpanel     admin API — hamma narsa
frontend/js/
  i18n.js + translations.js   3 til
  alarm.js                    ovozli budilnik
  map.js + vendor/leaflet     xarita (plitkalar OpenStreetMap)
  screens/                    har bir rol uchun ekranlar
```

> Barcha dorixonalar, haydovchilar, narxlar va sotuv tarixi o'ylab topilgan **demo ma'lumotlar**.
