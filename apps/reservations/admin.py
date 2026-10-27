from django.contrib import admin

from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "inventory", "quantity", "status", "code", "expires_at")
    list_filter = ("status",)
