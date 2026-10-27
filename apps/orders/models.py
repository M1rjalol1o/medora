from django.conf import settings
from django.db import models


class Order(models.Model):
    """Mijozning bitta umumiy buyurtmasi. Bir nechta dorixonadan bo'lsa ham to'lov BITTA."""

    class Status(models.TextChoices):
        AWAITING_PAYMENT = "awaiting_payment", "To'lov kutilmoqda"
        CONFIRMED = "confirmed", "Qabul qilindi"
        PREPARING = "preparing", "Tayyorlanmoqda"
        READY = "ready", "Tayyor"
        DELIVERING = "delivering", "Yo'lda"
        COMPLETED = "completed", "Yakunlandi"
        CANCELLED = "cancelled", "Bekor qilindi"

    class Fulfillment(models.TextChoices):
        DELIVERY = "delivery", "Yetkazib berish"
        PICKUP = "pickup", "O'zim olib ketaman"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Karta"
        CASH = "cash", "Naqd"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AWAITING_PAYMENT)
    fulfillment = models.CharField(max_length=10, choices=Fulfillment.choices, default=Fulfillment.DELIVERY)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CARD)
    is_paid = models.BooleanField(default=False)
    address = models.CharField(max_length=300, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    comment = models.CharField(max_length=300, blank=True)
    items_total = models.PositiveIntegerField(default=0)
    delivery_fee = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    delivery_code = models.CharField(max_length=4, blank=True)       # mijoz haydovchiga aytadi
    prescription = models.ForeignKey("prescriptions.Prescription", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PharmacyOrder(models.Model):
    """Har bir dorixona uchun alohida sub-buyurtma."""

    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        ACCEPTED = "accepted", "Qabul qilindi"
        READY = "ready", "Tayyor"
        PICKED_UP = "picked_up", "Haydovchi oldi"
        ISSUED = "issued", "Mijozga berildi"
        REJECTED = "rejected", "Rad etildi"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="pharmacy_orders")
    pharmacy = models.ForeignKey("pharmacies.Pharmacy", on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    subtotal = models.PositiveIntegerField(default=0)
    pickup_code = models.CharField(max_length=4)                     # olib ketishda aytiladi
    rx_verified = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class OrderItem(models.Model):
    pharmacy_order = models.ForeignKey(PharmacyOrder, on_delete=models.CASCADE, related_name="items")
    inventory = models.ForeignKey("pharmacies.Inventory", on_delete=models.PROTECT)
    medicine_name = models.CharField(max_length=250)
    quantity = models.PositiveIntegerField()
    price = models.PositiveIntegerField()
    requires_prescription = models.BooleanField(default=False)
