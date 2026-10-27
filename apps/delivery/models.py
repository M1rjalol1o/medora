from django.conf import settings
from django.db import models


class TaxiPark(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True)
    commission_percent = models.PositiveSmallIntegerField(default=15)    # park ulushi yetkazish narxidan
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Driver(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="driver_profile")
    park = models.ForeignKey(TaxiPark, on_delete=models.CASCADE, related_name="drivers")
    car_model = models.CharField(max_length=100)
    car_number = models.CharField(max_length=20)
    is_online = models.BooleanField(default=False)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5)

    def __str__(self):
        return f"{self.user.first_name} · {self.car_number}"


class Delivery(models.Model):
    class Status(models.TextChoices):
        SEARCHING = "searching", "Haydovchi qidirilmoqda"
        ASSIGNED = "assigned", "Haydovchi biriktirildi"
        PICKING = "picking", "Dorixonalardan olinmoqda"
        DELIVERING = "delivering", "Yo'lda"
        DELIVERED = "delivered", "Yetkazildi"
        CANCELLED = "cancelled", "Bekor qilindi"

    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="delivery")
    driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name="deliveries")
    park = models.ForeignKey(TaxiPark, null=True, blank=True, on_delete=models.SET_NULL, related_name="deliveries")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SEARCHING)
    fee = models.PositiveIntegerField(default=0)                 # mijoz to'laydigan yetkazish narxi
    distance_km = models.FloatField(default=0)
    driver_earning = models.PositiveIntegerField(default=0)
    park_earning = models.PositiveIntegerField(default=0)
    platform_earning = models.PositiveIntegerField(default=0)
    cash_collected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class DeliveryStop(models.Model):
    """Marshrut nuqtasi: dorixonalardan olish (pickup) va mijozga topshirish (dropoff)."""

    class Kind(models.TextChoices):
        PICKUP = "pickup", "Olish"
        DROPOFF = "dropoff", "Topshirish"

    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="stops")
    sequence = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=10, choices=Kind.choices)
    pharmacy_order = models.ForeignKey("orders.PharmacyOrder", null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    lat = models.FloatField()
    lng = models.FloatField()
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["sequence"]
