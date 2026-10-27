from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class ReservationQuerySet(models.QuerySet):
    def active(self):
        """Hali amal qilayotgan bronlar (qoldiqni band qiladi)."""
        return self.filter(
            status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED],
            expires_at__gt=timezone.now(),
        )

    def expire_overdue(self):
        return self.filter(
            status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED],
            expires_at__lte=timezone.now(),
        ).update(status=Reservation.Status.EXPIRED)


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        CONFIRMED = "confirmed", "Tasdiqlandi"
        COMPLETED = "completed", "Berildi"
        CANCELLED = "cancelled", "Bekor qilindi"
        EXPIRED = "expired", "Muddati o'tdi"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    inventory = models.ForeignKey("pharmacies.Inventory", on_delete=models.CASCADE, related_name="reservations")
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    code = models.CharField(max_length=6)               # dorixonada aytiladigan kod
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    objects = ReservationQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    hold_minutes = models.PositiveIntegerField(default=20)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=self.hold_minutes)
        super().save(*args, **kwargs)


def hold_minutes_for(pharmacy, lat=None, lng=None) -> int:
    """Bron muddati = mijozning dorixonagacha PIYODA yo'l vaqti + 20 daqiqa (yuqori chegara bilan)."""
    from apps.search.geo import haversine_km, travel_minutes
    if lat is None or lng is None:
        return settings.RESERVATION_HOLD_MINUTES
    walk = travel_minutes(haversine_km(lat, lng, pharmacy.lat, pharmacy.lng), "walk")
    total = int(round(walk)) + settings.RESERVATION_EXTRA_MINUTES
    return max(settings.RESERVATION_EXTRA_MINUTES, min(total, settings.RESERVATION_MAX_MINUTES))
