"""
Demo ma'lumot: Toshkentdagi o'ylab topilgan dorixonalar, dorilar, qoldiq va
45 kunlik sintetik sotuv tarixi.  Ishga tushirish:  python manage.py seed_demo
Diqqat: barcha nomlar va raqamlar o'ylab topilgan (demo uchun).
"""
import math
import os
import random
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Medicine
from apps.delivery.models import Delivery, Driver, TaxiPark
from apps.orders.models import Order
from apps.payments.models import PaymentCard
from apps.prescriptions.models import MedicationCourse, Prescription
from apps.pharmacies.models import Inventory, Pharmacy, SaleRecord
from apps.reservations.models import Reservation

User = get_user_model()
PASSWORD = "demo1234"

# (nomi, manzil, lat, lng, 24 soatmi, trafik koeffitsienti)
PHARMACIES = [
    ("Shifo Dorixona №1", "Amir Temur ko'chasi, 12", 41.3195, 69.2790, True, 1.6),     # yaqin, gavjum
    ("Salomat Farm", "Mustaqillik maydoni yonida", 41.3135, 69.2620, True, 1.0),
    ("Dori-Darmon 24", "Chilonzor, 9-kvartal", 41.2850, 69.2040, True, 1.1),
    ("Hayot Apteka", "Yunusobod, 4-mavze", 41.3640, 69.2860, True, 0.9),
    ("Malham Dorixona", "Mirobod ko'chasi, 30", 41.2960, 69.2830, False, 1.2),
    ("Sog'lom Oila", "Shayxontohur, Navoiy ko'chasi", 41.3260, 69.2400, False, 0.8),
    ("Darmon Plus", "Yakkasaroy, Bobur ko'chasi", 41.2890, 69.2560, True, 1.0),
    ("Ziyo Farm", "Olmazor, Qorasaroy", 41.3480, 69.2240, False, 0.7),
    ("Nur Dorixona", "Mirzo Ulug'bek, Buyuk Ipak Yo'li", 41.3270, 69.3350, True, 1.3),
    ("Barhayot", "Sergeli, 7-mavze", 41.2280, 69.2190, False, 0.6),
    ("Oq Ilon Apteka", "Yashnobod, Mahtumquli", 41.2990, 69.3290, True, 0.9),
    ("Sihat Markaz Dorixonasi", "Yunusobod, Amir Temur shoh ko'chasi", 41.3420, 69.2850, True, 1.4),
]

# (nomi, MNN, shakli, dozasi, ishlab chiqaruvchi, retseptli, muqobil nomlar, mashhurlik)
MEDICINES = [
    ("Paratsetamol", "Paracetamol", "tabletka", "500 mg", "Demo Farm", False, "paracetamol, парацетамол, paratsetamol, panadol", 10),
    ("Ibuprofen", "Ibuprofen", "tabletka", "400 mg", "Demo Farm", False, "ибупрофен, nurofen, нурофен", 8),
    ("Sitramon", "Asetilsalitsil kislota + kofein", "tabletka", "", "Demo Farm", False, "цитрамон, citramon", 7),
    ("Drotaverin", "Drotaverine", "tabletka", "40 mg", "Demo Farm", False, "дротаверин, no-shpa, но-шпа, noshpa", 7),
    ("Loratadin", "Loratadine", "tabletka", "10 mg", "Demo Farm", False, "лоратадин, allergiya", 5),
    ("Omeprazol", "Omeprazole", "kapsula", "20 mg", "Demo Farm", False, "омепразол, omez, омез", 5),
    ("Metamizol (Analgin)", "Metamizole", "tabletka", "500 mg", "Demo Farm", False, "analgin, анальгин, метамизол", 6),
    ("Atsetilsalitsil kislota", "Acetylsalicylic acid", "tabletka", "100 mg", "Demo Farm", False, "aspirin, аспирин", 4),
    ("Ambroksol", "Ambroxol", "sirop", "15 mg/5 ml", "Demo Farm", False, "амброксол, lazolvan, лазолван, yo'tal", 5),
    ("Diosmektit", "Diosmectite", "kukun", "3 g", "Demo Farm", False, "smekta, смекта, диосмектит", 4),
    ("Rehidratatsiya tuzi", "ORS", "kukun", "", "Demo Farm", False, "regidron, регидрон", 3),
    ("Askorbin kislota", "Ascorbic acid", "tabletka", "500 mg", "Demo Farm", False, "vitamin c, витамин с, аскорбиновая", 4),
    ("Loperamid", "Loperamide", "kapsula", "2 mg", "Demo Farm", False, "лоперамид, imodium", 3),
    ("Amlodipin", "Amlodipine", "tabletka", "5 mg", "Demo Farm", False, "амлодипин, bosim", 3),
    ("Lizinopril", "Lisinopril", "tabletka", "10 mg", "Demo Farm", False, "лизиноприл", 2),
    ("Metformin", "Metformin", "tabletka", "500 mg", "Demo Farm", False, "метформин, glyukofaj, qand", 3),
    ("Setirizin", "Cetirizine", "tabletka", "10 mg", "Demo Farm", False, "цетиризин, zirtek", 3),
    ("Ksilometazolin", "Xylometazoline", "burun spreyi", "0.1%", "Demo Farm", False, "ксилометазолин, burun tomchi", 4),
    ("Nimesulid", "Nimesulide", "kukun", "100 mg", "Demo Farm", False, "нимесулид, nise, найз", 4),
    ("Amoksitsillin", "Amoxicillin", "kapsula", "500 mg", "Demo Farm", True, "амоксициллин, antibiotik", 3),
    ("Azitromitsin", "Azithromycin", "tabletka", "500 mg", "Demo Farm", True, "азитромицин, sumamed", 2),
    ("Seftriakson", "Ceftriaxone", "ukol kukuni", "1 g", "Demo Farm", True, "цефтриаксон, ukol", 2),
]

# Kun davomida xaridorlar taqsimoti (soat -> ulush)
DAY_PROFILE = {h: w for h, w in zip(range(24), [
    0.2, 0.1, 0.1, 0.05, 0.05, 0.1, 0.3, 0.6, 1.0, 1.3, 1.4, 1.3,
    1.1, 1.0, 1.0, 1.1, 1.2, 1.4, 1.6, 1.5, 1.2, 0.9, 0.6, 0.4])}


def poisson(lam: float) -> int:
    if lam <= 0:
        return 0
    l, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= random.random()
        if p <= l:
            return k
        k += 1


class Command(BaseCommand):
    help = "Demo dorixonalar, dorilar, qoldiq va sotuv tarixini yaratadi"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=45)

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(42)
        self.stdout.write("Eski demo ma'lumot o'chirilmoqda...")
        Reservation.objects.all().delete()
        Delivery.objects.all().delete()
        Order.objects.all().delete()
        PaymentCard.objects.all().delete()
        Prescription.objects.all().delete()
        MedicationCourse.objects.all().delete()
        Driver.objects.all().delete()
        TaxiPark.objects.all().delete()
        SaleRecord.objects.all().delete()
        Inventory.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        Pharmacy.objects.all().delete()
        Medicine.objects.all().delete()

        meds = []
        for name, inn, form, dose, man, rx, aliases, pop in MEDICINES:
            m = Medicine.objects.create(name=name, inn=inn, form=form, dosage=dose, manufacturer=man,
                                        requires_prescription=rx, aliases=aliases)
            meds.append((m, pop))

        pharmacies = []
        for i, (name, addr, lat, lng, h24, traffic) in enumerate(PHARMACIES, start=1):
            ph = Pharmacy.objects.create(
                name=name, address=addr, lat=lat, lng=lng, is_24h=h24,
                phone=f"+998 71 200-{10 + i:02d}-{30 + i:02d}",
                opens_at=None if h24 else time(8, 0), closes_at=None if h24 else time(22, 0),
            )
            pharmacies.append((ph, traffic))

        # Qoldiq
        today = timezone.localdate()
        inventories = []
        for ph, traffic in pharmacies:
            for m, pop in meds:
                if random.random() < 0.15:          # har dorixonada hamma dori bo'lmaydi
                    continue
                qty = random.choice([0, 1, 2, 3, 5, 8, 12, 15, 20, 30, 40]) if random.random() < 0.9 else 0
                base_price = {10: 4000, 8: 9000, 7: 6000}.get(pop, random.randint(8, 60) * 1000)
                inventories.append(Inventory(
                    pharmacy=ph, medicine=m, quantity=qty,
                    price=int(base_price * random.uniform(0.85, 1.25) / 100) * 100,
                    min_stock=5,
                    # ~15% dorilarning muddati 3 oy ichida tugaydi (dorixona panelida ko'rinishi uchun)
                    expiry_date=today + timedelta(days=random.randint(5, 85) if random.random() < 0.15
                                                  else random.randint(120, 700)),
                ))
        Inventory.objects.bulk_create(inventories)

        # Demo ssenariy: Paratsetamol — yaqin dorixonada 1 dona (tez sotiladi), uzoqroqda 20 dona
        para = meds[0][0]
        near, far = pharmacies[0][0], pharmacies[8][0]
        Inventory.objects.update_or_create(pharmacy=near, medicine=para, defaults={"quantity": 1, "price": 4200})
        Inventory.objects.update_or_create(pharmacy=far, medicine=para, defaults={"quantity": 20, "price": 3900})
        # Markazdagi boshqa yaqin dorixonalarda tugagan — shunda tanlov qiziqroq bo'ladi
        for ph, _ in (pharmacies[4], pharmacies[1]):
            Inventory.objects.filter(pharmacy=ph, medicine=para).update(quantity=0)

        # Sotuv tarixi (soatlik)
        self.stdout.write(f"{opts['days']} kunlik sotuv tarixi yaratilmoqda...")
        records = []
        for ph, traffic in pharmacies:
            for m, pop in meds:
                daily = pop * traffic * random.uniform(0.6, 1.4) * 1.6     # kuniga o'rtacha dona
                if ph == near and m == para:
                    daily = 40                                            # gavjum joy: soatiga ~2-3 dona
                hours = range(24) if ph.is_24h else range(8, 22)
                weight_sum = sum(DAY_PROFILE[h] for h in hours)
                for d in range(opts["days"], 0, -1):
                    day = today - timedelta(days=d)
                    season = 1.2 if day.weekday() < 5 else 0.9
                    for h in hours:
                        q = poisson(daily * season * DAY_PROFILE[h] / weight_sum)
                        if q:
                            records.append(SaleRecord(pharmacy=ph, medicine=m, date=day, hour=h, quantity=q))
        SaleRecord.objects.bulk_create(records, batch_size=5000)

        # Bitta chegirma namunasi
        Inventory.objects.filter(pharmacy=far, medicine=meds[1][0]).update(
            discount_percent=20, expiry_date=today + timedelta(days=25), quantity=14)

        # Taksoparklar va haydovchilar
        parks = [TaxiPark.objects.create(name="Tez Taksi Park", phone="+998 71 300-10-10", commission_percent=15),
                 TaxiPark.objects.create(name="Shahar Yetkazish", phone="+998 71 300-20-20", commission_percent=12)]
        cars = [("Chevrolet Cobalt", "01 A 123 BC"), ("Chevrolet Nexia 3", "01 B 456 DE"),
                ("Chevrolet Lacetti", "01 C 789 FG"), ("Chevrolet Spark", "01 D 321 HK"),
                ("Kia K5", "01 E 654 LM"), ("Chevrolet Damas", "01 F 987 NP")]
        names = ["Akmal", "Bekzod", "Sardor", "Jasur", "Dilshod", "Otabek"]
        for i, ((model, number), name) in enumerate(zip(cars, names), start=1):
            u = User.objects.create_user(f"driver{i}", password=PASSWORD, first_name=name,
                                         phone=f"+998 93 100-00-{i:02d}", role=User.Role.DRIVER)
            ph = pharmacies[(i * 3) % len(pharmacies)][0]
            Driver.objects.create(user=u, park=parks[(i - 1) % 2], car_model=model, car_number=number,
                                  is_online=i <= 3, lat=ph.lat + 0.004, lng=ph.lng - 0.004)
        for i, park in enumerate(parks, start=1):
            User.objects.create_user(f"park{i}", password=PASSWORD, first_name=f"{park.name} dispetcheri",
                                     role=User.Role.TAXIPARK, taxi_park=park)

        # Foydalanuvchilar
        User.objects.create_user("demo", password=PASSWORD, first_name="Demo mijoz", phone="+998 90 000-00-00")
        for i, (ph, _) in enumerate(pharmacies, start=1):
            User.objects.create_user(f"dorixona{i}", password=PASSWORD, first_name=f"{ph.name} xodimi",
                                     role=User.Role.PHARMACY, pharmacy=ph)
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", password=os.getenv("ADMIN_PASSWORD", "admin1234"), role=User.Role.ADMIN,
                                          first_name="Administrator")

        self.stdout.write(self.style.SUCCESS(
            f"Tayyor: {len(pharmacies)} dorixona, {len(meds)} dori, {Inventory.objects.count()} qoldiq yozuvi, "
            f"{len(records)} sotuv yozuvi.\n"
            f"Kirish: mijoz demo · dorixona dorixona1 · haydovchi driver1 · taksopark park1 "
            f"(parol {PASSWORD}) · admin: admin / ADMIN_PASSWORD (standart admin1234)"
        ))
