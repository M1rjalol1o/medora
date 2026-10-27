from django.contrib import admin

from .models import MedicationCourse, Prescription, PrescriptionItem

admin.site.register(Prescription)
admin.site.register(PrescriptionItem)
admin.site.register(MedicationCourse)
