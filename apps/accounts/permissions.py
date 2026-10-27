from rest_framework.permissions import BasePermission


class IsPharmacyStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_pharmacy_staff)


class IsDriver(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "driver" and hasattr(u, "driver_profile"))


class IsTaxiPark(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "taxipark" and u.taxi_park_id)


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_platform_admin)
