from django.contrib import admin

from .models import Notification, StockWatch

admin.site.register(StockWatch)
admin.site.register(Notification)
