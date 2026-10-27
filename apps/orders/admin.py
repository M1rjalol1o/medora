from django.contrib import admin

from .models import Order, OrderItem, PharmacyOrder

admin.site.register(Order)
admin.site.register(PharmacyOrder)
admin.site.register(OrderItem)
