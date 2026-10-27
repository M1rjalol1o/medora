from django.conf import settings
from django.db import models


class Prescription(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Yuklandi"
        PARSED = "parsed", "Tahlil qilindi"
        CONFIRMED = "confirmed", "Tasdiqlandi"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="prescriptions")
    image = models.ImageField(upload_to="prescriptions/%Y/%m/", null=True, blank=True)
    raw_text = models.TextField(blank=True)
    ocr_engine = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="items")
    medicine = models.ForeignKey("catalog.Medicine", null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200)
    dose = models.CharField(max_length=60, blank=True)
    times_per_day = models.PositiveSmallIntegerField(default=1)
    duration_days = models.PositiveSmallIntegerField(default=5)
    note = models.CharField(max_length=200, blank=True)
    confidence = models.FloatField(default=0)


class MedicationCourse(models.Model):
    """Dori qabul qilish jadvali (budilnik)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses")
    prescription_item = models.ForeignKey(PrescriptionItem, null=True, blank=True, on_delete=models.SET_NULL)
    medicine_name = models.CharField(max_length=200)
    dose = models.CharField(max_length=60, blank=True)
    times = models.JSONField(default=list)          # ["08:00", "14:00", "20:00"]
    start_date = models.DateField()
    end_date = models.DateField()
    note = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class IntakeLog(models.Model):
    course = models.ForeignKey(MedicationCourse, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField()
    time = models.CharField(max_length=5)
    status = models.CharField(max_length=10, default="taken")       # taken / skipped
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "date", "time")
