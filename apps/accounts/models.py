from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Platforma foydalanuvchisi. Rol orqali panel va ruxsatlar ajratiladi."""

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Mijoz"
        PHARMACY = "pharmacy", "Dorixona xodimi"
        DRIVER = "driver", "Haydovchi"
        TAXIPARK = "taxipark", "Taksopark"
        ADMIN = "admin", "Administrator"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=20, blank=True)
    language = models.CharField(max_length=5, default="uz")          # uz / ru / en
    pharmacy = models.ForeignKey(
        "pharmacies.Pharmacy", null=True, blank=True, on_delete=models.SET_NULL, related_name="staff"
    )
    taxi_park = models.ForeignKey(
        "delivery.TaxiPark", null=True, blank=True, on_delete=models.SET_NULL, related_name="managers"
    )

    @property
    def is_pharmacy_staff(self) -> bool:
        return self.role == self.Role.PHARMACY and self.pharmacy_id is not None

    @property
    def is_platform_admin(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser
