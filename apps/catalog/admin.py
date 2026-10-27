from django.contrib import admin

from .models import Medicine


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ("name", "dosage", "form", "inn", "requires_prescription")
    search_fields = ("name", "inn", "aliases")
