from django.contrib import admin

from .models import Delivery, DeliveryStop, Driver, TaxiPark

admin.site.register(TaxiPark)
admin.site.register(Driver)


class StopInline(admin.TabularInline):
    model = DeliveryStop
    extra = 0


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "driver", "status", "fee", "created_at")
    inlines = [StopInline]
