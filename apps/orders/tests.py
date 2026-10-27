from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Medicine
from apps.delivery.models import Driver, TaxiPark
from apps.pharmacies.models import Inventory, Pharmacy
from apps.prescriptions.parser import parse

User = get_user_model()


class FullFlowTests(TestCase):
    def setUp(self):
        self.c = APIClient()
        self.m1 = Medicine.objects.create(name="Paratsetamol", dosage="500 mg", aliases="парацетамол")
        self.m2 = Medicine.objects.create(name="Ibuprofen", dosage="400 mg", aliases="ибупрофен")
        self.rx = Medicine.objects.create(name="Amoksitsillin", dosage="500 mg", requires_prescription=True)
        self.p1 = Pharmacy.objects.create(name="A", address="a", lat=41.31, lng=69.27, is_24h=True)
        self.p2 = Pharmacy.objects.create(name="B", address="b", lat=41.33, lng=69.30, is_24h=True)
        self.i1 = Inventory.objects.create(pharmacy=self.p1, medicine=self.m1, quantity=5, price=4000)
        self.i2 = Inventory.objects.create(pharmacy=self.p2, medicine=self.m2, quantity=5, price=10000,
                                           discount_percent=20, expiry_date=timezone.localdate() + timedelta(days=10))
        self.i3 = Inventory.objects.create(pharmacy=self.p1, medicine=self.rx, quantity=3, price=20000)
        self.user = User.objects.create_user("u", password="secret12", first_name="Ali")
        self.s1 = User.objects.create_user("s1", password="x" * 8, role="pharmacy", pharmacy=self.p1)
        self.s2 = User.objects.create_user("s2", password="x" * 8, role="pharmacy", pharmacy=self.p2)
        self.park = TaxiPark.objects.create(name="Park", commission_percent=15)
        du = User.objects.create_user("d", password="x" * 8, role="driver")
        self.driver = Driver.objects.create(user=du, park=self.park, car_model="Cobalt", car_number="01A",
                                            is_online=True, lat=41.3, lng=69.26)
        self.admin = User.objects.create_user("adm", password="x" * 8, role="admin")
        self.parkuser = User.objects.create_user("pk", password="x" * 8, role="taxipark", taxi_park=self.park)

    def as_(self, u):
        self.c.force_authenticate(u)

    def add_card(self, number="8600000000000007"):
        self.as_(self.user)
        r = self.c.post("/api/payments/cards/", {"number": number, "expiry": "12/30"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        bad = self.c.post("/api/payments/cards/verify/", {"session": r.json()["session"], "code": "000000x"}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = self.c.post("/api/payments/cards/verify/", {"session": r.json()["session"],
                                                          "code": r.json()["sandbox_code"]}, format="json")
        self.assertEqual(ok.status_code, 201)
        self.assertNotIn(number[4:12], ok.json()["masked"])          # to'liq raqam saqlanmaydi
        return ok.json()["id"]

    def test_invalid_card_rejected(self):
        self.as_(self.user)
        r = self.c.post("/api/payments/cards/", {"number": "8600000000000005", "expiry": "12/30"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_multi_pharmacy_single_payment_delivery(self):
        card = self.add_card()
        items = [{"inventory_id": self.i1.id, "quantity": 2}, {"inventory_id": self.i2.id, "quantity": 1}]
        q = self.c.post("/api/orders/quote/", {"items": items, "fulfillment": "delivery", "lat": 41.32, "lng": 69.28},
                        format="json").json()
        self.assertEqual(q["items_total"], 2 * 4000 + 8000)       # 20% chegirma
        self.assertEqual(q["pharmacies"], 2)
        r = self.c.post("/api/orders/", {"items": items, "fulfillment": "delivery", "payment_method": "card",
                                         "lat": 41.32, "lng": 69.28, "address": "Uy"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        o = r.json()
        self.assertEqual(len(o["pharmacy_orders"]), 2)
        self.assertEqual(o["total"], q["total"])
        self.assertEqual(len(o["delivery"]["stops"]), 3)
        # Haydovchi to'lanmagan buyurtmani ko'rmaydi
        self.as_(self.driver.user)
        self.assertEqual(self.c.get("/api/driver/available/").json(), [])
        # BITTA to'lov
        self.as_(self.user)
        p = self.c.post(f"/api/payments/orders/{o['id']}/pay/", {"card_id": card}, format="json")
        self.assertEqual(p.status_code, 200, p.content)
        self.assertEqual(p.json()["amount"], o["total"])
        self.assertEqual(self.c.post(f"/api/payments/orders/{o['id']}/pay/", {"card_id": card}, format="json").status_code, 400)
        # Haydovchi qabul qiladi
        self.as_(self.driver.user)
        tasks = self.c.get("/api/driver/available/").json()
        self.assertEqual(len(tasks), 1)
        did = tasks[0]["id"]
        self.assertEqual(self.c.post(f"/api/driver/deliveries/{did}/accept/").status_code, 200)
        stops = self.c.get("/api/driver/current/").json()["stops"]
        # Dorixona tayyorlamaguncha olib bo'lmaydi
        self.assertEqual(self.c.post(f"/api/driver/stops/{stops[0]['id']}/done/").status_code, 400)
        for staff in (self.s1, self.s2):
            self.as_(staff)
            po = self.c.get("/api/panel/orders/").json()[0]
            self.assertEqual(self.c.post(f"/api/panel/orders/{po['id']}/accept/").status_code, 200)
            self.assertEqual(self.c.post(f"/api/panel/orders/{po['id']}/ready/").status_code, 200)
        self.as_(self.driver.user)
        for s in stops[:2]:
            self.assertEqual(self.c.post(f"/api/driver/stops/{s['id']}/done/").status_code, 200)
        self.assertEqual(self.c.post(f"/api/driver/stops/{stops[2]['id']}/done/", {"code": "xxxx"}, format="json").status_code, 400)
        r = self.c.post(f"/api/driver/stops/{stops[2]['id']}/done/", {"code": o["delivery_code"]}, format="json")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["status"], "delivered")
        self.assertEqual(d["driver_earning"] + d["park_earning"] + d["fee"] * 10 // 100, d["fee"])
        self.as_(self.user)
        self.assertEqual(self.c.get(f"/api/orders/{o['id']}/").json()["status"], "completed")
        # Admin hammasini ko'radi, mijoz admin API'ga kira olmaydi
        self.assertEqual(self.c.get("/api/admin/stats/").status_code, 403)
        self.as_(self.admin)
        self.assertEqual(self.c.get("/api/admin/stats/").json()["orders_today"], 1)
        self.assertEqual(len(self.c.get("/api/admin/payments/").json()), 1)
        self.as_(self.parkuser)
        self.assertEqual(self.c.get("/api/park/dashboard/").json()["today_deliveries"], 1)

    def test_cash_pickup_and_rx(self):
        self.as_(self.user)
        r = self.c.post("/api/orders/", {"items": [{"inventory_id": self.i3.id, "quantity": 1}],
                                         "fulfillment": "pickup", "payment_method": "cash"}, format="json")
        self.assertEqual(r.status_code, 409)                      # retsept kerak
        rx = self.c.post("/api/prescriptions/", {"text": "Amoksitsillin 500 mg kuniga 3 mahal 7 kun"}, format="multipart").json()
        self.assertEqual(rx["items"][0]["times_per_day"], 3)
        r = self.c.post("/api/orders/", {"items": [{"inventory_id": self.i3.id, "quantity": 1}], "prescription_id": rx["id"],
                                         "fulfillment": "pickup", "payment_method": "cash"}, format="json")
        self.assertEqual(r.status_code, 201)
        o = r.json()
        self.assertEqual(o["status"], "confirmed")
        self.as_(self.s1)
        po = self.c.get("/api/panel/orders/").json()[0]
        self.assertEqual(self.c.post(f"/api/panel/orders/{po['id']}/ready/").status_code, 400)   # retsept tekshirilmagan
        self.c.post(f"/api/panel/orders/{po['id']}/verify_rx/")
        self.assertEqual(self.c.post(f"/api/panel/orders/{po['id']}/ready/").status_code, 200)
        code = o["pharmacy_orders"][0]["pickup_code"]
        self.assertEqual(self.c.post(f"/api/panel/orders/{po['id']}/issue/", {"code": code}, format="json").status_code, 200)
        self.as_(self.user)
        o = self.c.get(f"/api/orders/{o['id']}/").json()
        self.assertEqual((o["status"], o["is_paid"]), ("completed", True))

    def test_cancel_restores_stock(self):
        self.as_(self.user)
        o = self.c.post("/api/orders/", {"items": [{"inventory_id": self.i1.id, "quantity": 3}],
                                         "fulfillment": "pickup", "payment_method": "cash"}, format="json").json()
        self.i1.refresh_from_db()
        self.assertEqual(self.i1.quantity, 2)
        self.c.post(f"/api/orders/{o['id']}/cancel/")
        self.i1.refresh_from_db()
        self.assertEqual(self.i1.quantity, 5)

    def test_reservation_hold_is_walk_time_plus_20(self):
        self.as_(self.user)
        near = self.c.post("/api/reservations/", {"inventory_id": self.i1.id, "lat": 41.3101, "lng": 69.2701},
                           format="json").json()
        self.assertEqual(near["hold_minutes"], 20)
        far = self.c.post("/api/reservations/", {"inventory_id": self.i1.id, "lat": 41.40, "lng": 69.40},
                          format="json").json()
        self.assertGreater(far["hold_minutes"], 120)
        self.assertLessEqual(far["hold_minutes"], 240)

    def test_expiring_panel(self):
        self.as_(self.s2)
        r = self.c.get("/api/panel/expiring/").json()
        self.assertEqual(r["items"][0]["medicine"]["name"], "Ibuprofen")


class ParserTests(TestCase):
    def setUp(self):
        Medicine.objects.create(name="Paratsetamol", dosage="500 mg", aliases="парацетамол, paracetamol")
        Medicine.objects.create(name="Ibuprofen", dosage="400 mg", aliases="ибупрофен")

    def test_three_languages(self):
        r = parse("1) Paratsetamol 500 mg kuniga 3 mahal 5 kun\n2) Ибупрофен 400мг 2 раза в день 7 дней\n"
                  "Paracetamol 500mg 4 times a day for 3 days")
        self.assertEqual([(x["name"], x["times_per_day"], x["duration_days"]) for x in r],
                         [("Paratsetamol", 3, 5), ("Ibuprofen", 2, 7), ("Paratsetamol", 4, 3)])


class BasketTests(TestCase):
    """3 ta dori: yaqin dorixonada 2 tasi bor, uzoqroqda hammasi bor."""

    def setUp(self):
        self.ms = [Medicine.objects.create(name=n, dosage="1") for n in ("Aaa", "Bbb", "Ccc")]
        self.near = Pharmacy.objects.create(name="Yaqin", address="a", lat=41.3115, lng=69.2800, is_24h=True)
        self.full = Pharmacy.objects.create(name="Hammasi", address="b", lat=41.3250, lng=69.2950, is_24h=True)
        for m in self.ms[:2]:
            Inventory.objects.create(pharmacy=self.near, medicine=m, quantity=10, price=1000)
        for m in self.ms:
            Inventory.objects.create(pharmacy=self.full, medicine=m, quantity=10, price=1200)

    def test_all_in_one_alternative(self):
        r = APIClient().post("/api/basket/", {"items": [{"medicine_id": m.id} for m in self.ms],
                                              "lat": 41.3111, "lng": 69.2797}, format="json").json()
        self.assertEqual(r["nearest"]["pharmacy"]["name"], "Yaqin")
        self.assertEqual(r["nearest"]["missing"], ["Ccc"])
        kinds = {k: o for o in r["options"] for k in [o["kind"]] + o.get("also", [])}
        self.assertIn("all_in_one", kinds)
        self.assertEqual(kinds["all_in_one"]["stops"][0]["pharmacy"]["name"], "Hammasi")
        self.assertEqual(sum(len(s["items"]) for s in kinds["recommended"]["stops"]), 3)
