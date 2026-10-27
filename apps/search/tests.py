from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Medicine
from apps.pharmacies.models import Inventory, Pharmacy, SaleRecord

from .prediction import poisson_prob_less_than


class PoissonTests(TestCase):
    def test_edge_cases(self):
        self.assertEqual(poisson_prob_less_than(0, 1.0), 0.0)     # dori yo'q
        self.assertEqual(poisson_prob_less_than(5, 0.0), 1.0)     # hech kim sotib olmaydi

    def test_one_left(self):
        # 1 dona, o'rtacha 0.667 sotuv -> P = e^-0.667 ≈ 0.513
        self.assertAlmostEqual(poisson_prob_less_than(1, 2 / 3), 0.513, places=2)

    def test_more_stock_is_safer(self):
        self.assertGreater(poisson_prob_less_than(20, 1.0), poisson_prob_less_than(1, 1.0))


class SearchAndReservationFlowTests(TestCase):
    def setUp(self):
        self.med = Medicine.objects.create(name="Paratsetamol", dosage="500 mg", aliases="парацетамол")
        self.near = Pharmacy.objects.create(name="Yaqin", address="a", lat=41.312, lng=69.280, is_24h=True)
        self.far = Pharmacy.objects.create(name="Uzoq", address="b", lat=41.340, lng=69.330, is_24h=True)
        self.inv_near = Inventory.objects.create(pharmacy=self.near, medicine=self.med, quantity=1, price=4000)
        Inventory.objects.create(pharmacy=self.far, medicine=self.med, quantity=20, price=3900)
        today = timezone.localdate()
        # Yaqin dorixonada tez sotiladi
        SaleRecord.objects.bulk_create([
            SaleRecord(pharmacy=self.near, medicine=self.med, date=today - timedelta(days=d), hour=h, quantity=4)
            for d in range(1, 15) for h in range(24)
        ])
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user("u", password="secret12")
        self.staff = User.objects.create_user("s", password="secret12", role=User.Role.PHARMACY, pharmacy=self.near)

    def test_cyrillic_search(self):
        r = self.client.get("/api/medicines/", {"q": "парац"})
        self.assertEqual(r.json()[0]["id"], self.med.id)

    def test_urgent_prefers_guaranteed(self):
        r = self.client.get(f"/api/medicines/{self.med.id}/offers/", {"mode": "urgent"}).json()
        self.assertEqual(r["offers"][0]["pharmacy"]["name"], "Uzoq")
        near = next(o for o in r["offers"] if o["pharmacy"]["name"] == "Yaqin")
        self.assertLess(near["probability"], 0.9)

    def test_reservation_holds_last_unit_and_completes(self):
        self.client.force_authenticate(self.user)
        r = self.client.post("/api/reservations/", {"inventory_id": self.inv_near.id}, format="json")
        self.assertEqual(r.status_code, 201)
        code, rid = r.json()["code"], r.json()["id"]
        # Oxirgi dona band — ikkinchi bron rad etiladi
        self.assertEqual(self.client.post("/api/reservations/", {"inventory_id": self.inv_near.id}, format="json").status_code, 409)
        # Dorixona xodimi kod bilan beradi
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post(f"/api/panel/reservations/{rid}/complete/", {"code": "x"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(f"/api/panel/reservations/{rid}/complete/", {"code": code}, format="json").status_code, 200)
        self.inv_near.refresh_from_db()
        self.assertEqual(self.inv_near.quantity, 0)

    def test_panel_requires_staff(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/panel/inventory/").status_code, 403)
