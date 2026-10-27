from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AppUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Platforma", {"fields": ("role", "phone", "pharmacy")}),)
    list_display = ("username", "role", "pharmacy", "phone", "is_staff")
