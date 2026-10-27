from django.conf import settings
from django.db import models


class PaymentCard(models.Model):
    """Saqlangan karta. Karta raqami SAQLANMAYDI — faqat provayder tokeni va oxirgi 4 raqam."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cards")
    token = models.CharField(max_length=100)          # provayder (Payme/Click) bergan token
    masked = models.CharField(max_length=25)          # 8600 •••• •••• 1234
    brand = models.CharField(max_length=20)           # Uzcard / Humo / Visa / Mastercard
    expiry = models.CharField(max_length=5)           # MM/YY
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CardVerification(models.Model):
    """Karta qo'shishda SMS kod bosqichi."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session = models.CharField(max_length=64, unique=True)
    pending_token = models.CharField(max_length=100)
    masked = models.CharField(max_length=25)
    brand = models.CharField(max_length=20)
    expiry = models.CharField(max_length=5)
    phone_hint = models.CharField(max_length=20)
    otp_hash = models.CharField(max_length=128)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        PAID = "paid", "To'landi"
        CASH_PENDING = "cash_pending", "Naqd — yetkazishda"
        FAILED = "failed", "Xato"
        REFUNDED = "refunded", "Qaytarildi"

    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="payments")
    amount = models.PositiveIntegerField()
    method = models.CharField(max_length=10)
    card = models.ForeignKey(PaymentCard, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=20, default="sandbox")
    provider_ref = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
