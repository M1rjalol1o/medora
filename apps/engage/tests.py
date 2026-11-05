from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Medicine
from apps.pharmacies.models import Inventory, Pharmacy

User = get_user_model()


class EngageTests(TestCase):
    def setUp(self):
        self.c = APIClient()
        self.gen = Medicine.objects.create(name="Ibuprofen", inn="Ibuprofen", dosage="400 mg")
        self.brand = Medicine.objects.create(name="Nurofen", inn="Ibuprofen", dosage="400 mg")
        self.ph = Pharmacy.objects.create(name="A", address="a", lat=41.31, lng=69.27, is_24h=True)
        self.ig = Inventory.objects.create(pharmacy=self.ph, medicine=self.gen, quantity=5, price=6000)
        self.ib = Inventory.objects.create(pharmacy=self.ph, medicine=self.brand, quantity=0, price=15000)
        self.u = User.objects.create_user("u", password="secret12", points=1000)
        self.staff = User.objects.create_user("s", password="x" * 8, role="pharmacy", pharmacy=self.ph)
        self.c.force_authenticate(self.u)

    def test_cheaper_alternative_and_search_log(self):
        r = self.c.get(f"/api/medicines/{self.brand.id}/offers/").json()
        alt = r["alternatives"][0]
        self.assertEqual((alt["medicine"]["name"], alt["min_price"], alt["cheaper"]), ("Ibuprofen", 6000, True))
        self.assertEqual(self.brand.searches.count(), 1)

    def test_back_in_stock_notification(self):
        self.assertEqual(self.c.post("/api/watches/", {"medicine_id": self.brand.id}, format="json").status_code, 201)
        self.assertTrue(self.c.get(f"/api/medicines/{self.brand.id}/offers/").json()["watching"])
        self.c.force_authenticate(self.staff)
        self.c.patch(f"/api/panel/inventory/{self.ib.id}/", {"quantity": 7}, format="json")
        self.c.force_authenticate(self.u)
        n = self.c.get("/api/notifications/").json()
        self.assertEqual(n["unread"], 1)
        self.assertEqual(n["items"][0]["kind"], "back_in_stock")
        self.assertFalse(self.c.get(f"/api/medicines/{self.brand.id}/offers/").json()["watching"])

    def test_points_redeem_earn_and_refund(self):
        items = [{"inventory_id": self.ig.id, "quantity": 2}]         # 12 000 so'm
        o = self.c.post("/api/orders/", {"items": items, "fulfillment": "pickup", "payment_method": "cash",
                                         "use_points": True}, format="json").json()
        self.assertEqual((o["points_used"], o["total"]), (1000, 11000))
        self.u.refresh_from_db()
        self.assertEqual(self.u.points, 0)
        self.c.post(f"/api/orders/{o['id']}/cancel/")
        self.u.refresh_from_db()
        self.assertEqual(self.u.points, 1000)                          # bekor qilinsa qaytadi

        o = self.c.post("/api/orders/", {"items": items, "fulfillment": "pickup", "payment_method": "cash"},
                        format="json").json()
        self.c.force_authenticate(self.staff)
        po = self.c.get("/api/panel/orders/").json()[0]
        self.c.post(f"/api/panel/orders/{po['id']}/ready/")
        self.c.post(f"/api/panel/orders/{po['id']}/issue/", {"code": o["pharmacy_orders"][0]["pickup_code"]},
                    format="json")
        self.u.refresh_from_db()
        self.assertEqual(self.u.points, 1000 + 120)                    # 1% keshbek

    def test_home_family_and_dashboard(self):
        m = self.c.post("/api/family/", {"name": "Onam", "relation": "ona"}, format="json").json()
        self.c.post("/api/courses/", {"medicine_name": "Amlodipin", "times": ["23:59"], "member": m["id"]},
                    format="json")
        self.assertEqual(len(self.c.get(f"/api/courses/?member={m['id']}").json()), 1)
        self.assertEqual(len(self.c.get("/api/courses/?member=me").json()), 0)
        st = self.c.get("/api/health/stats/").json()
        self.assertEqual([p["name"] for p in st["people"]][1], "Onam")
        h = self.c.get("/api/home/").json()
        self.assertEqual((h["points"], h["next_dose"]["member"]), (1000, "Onam"))
        self.c.get(f"/api/medicines/{self.gen.id}/offers/")
        self.c.force_authenticate(self.staff)
        d = self.c.get("/api/panel/dashboard/").json()
        self.assertEqual(len(d["week"]), 7)
        self.assertEqual(d["demand"][0]["name"], "Ibuprofen")
