from django.contrib import admin

from .models import Payment, PaymentCard

admin.site.register(Payment)
admin.site.register(PaymentCard)
