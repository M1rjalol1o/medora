from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Pharmacy(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    phone = models.CharField(max_length=30, blank=True)
    lat = models.FloatField()
    lng = models.FloatField()
    opens_at = models.TimeField(null=True, blank=True)
    closes_at = models.TimeField(null=True, blank=True)
    is_24h = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "pharmacies"

    def __str__(self):
        return self.name

    def is_open_now(self) -> bool:
        if self.is_24h:
            return True
        if not (self.opens_at and self.closes_at):
            return True
        now = timezone.localtime().time()
        if self.opens_at <= self.closes_at:
            return self.opens_at <= now <= self.closes_at
        return now >= self.opens_at or now <= self.closes_at  # tungi smena


class Inventory(models.Model):
    """Dorixonadagi real qoldiq (Pharmacy + Medicine)."""

    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name="inventory")
    medicine = models.ForeignKey("catalog.Medicine", on_delete=models.CASCADE, related_name="inventory")
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=12, decimal_places=0)   # so'mda
    min_stock = models.PositiveIntegerField(default=5)
    expiry_date = models.DateField(null=True, blank=True)
    # Muddati yaqin dorilarga chegirma (dorixona o'zi belgilaydi)
    discount_percent = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("pharmacy", "medicine")
        verbose_name_plural = "inventory"

    def __str__(self):
        return f"{self.pharmacy} — {self.medicine}: {self.quantity}"

    @property
    def final_price(self) -> int:
        return int(self.price * (100 - min(self.discount_percent, 90)) / 100 / 100) * 100

    @property
    def days_to_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.localdate()).days

    @property
    def reserved_quantity(self) -> int:
        from apps.reservations.models import Reservation
        return (
            Reservation.objects.active()
            .filter(inventory=self)
            .aggregate(s=Sum("quantity"))["s"]
            or 0
        )

    @property
    def available_quantity(self) -> int:
        """Sotish mumkin bo'lgan soni = qoldiq − faol bronlar."""
        return max(0, self.quantity - self.reserved_quantity)


class SaleRecord(models.Model):
    """Soatlik sotuv tarixi. Bashorat modeli shu ma'lumotdan o'rganadi.
    Real loyihada kassa/1C integratsiyasidan keladi."""

    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name="sales")
    medicine = models.ForeignKey("catalog.Medicine", on_delete=models.CASCADE, related_name="sales")
    date = models.DateField(db_index=True)
    hour = models.PositiveSmallIntegerField()           # 0..23
    quantity = models.PositiveIntegerField()

    class Meta:
        indexes = [models.Index(fields=["medicine", "pharmacy", "date"])]
