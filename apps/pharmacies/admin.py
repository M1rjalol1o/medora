from django.contrib import admin

from .models import Inventory, Pharmacy, SaleRecord


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "is_24h", "is_active")


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("pharmacy", "medicine", "quantity", "price", "updated_at")
    list_filter = ("pharmacy",)
    search_fields = ("medicine__name",)


admin.site.register(SaleRecord)
