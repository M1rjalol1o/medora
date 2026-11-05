from django.conf import settings
from django.db import models


class StockWatch(models.Model):
    """'Paydo bo'lsa xabar ber': dori (ixtiyoriy — aniq dorixonada) qayta paydo bo'lganda xabar."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watches")
    medicine = models.ForeignKey("catalog.Medicine", on_delete=models.CASCADE, related_name="watches")
    pharmacy = models.ForeignKey("pharmacies.Pharmacy", null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class Notification(models.Model):
    """Ilova ichidagi bildirishnoma. Matn frontendda 3 tilda `kind` + `data` dan yasaladi."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=30)              # back_in_stock / order_status / points
    data = models.JSONField(default=dict)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
