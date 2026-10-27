import secrets

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.pharmacies.models import Inventory

from apps.accounts.i18n import msg

from .models import Reservation, hold_minutes_for
from .serializers import ReservationCreateSerializer, ReservationSerializer


def _queryset():
    return Reservation.objects.select_related("inventory__medicine", "inventory__pharmacy", "user")


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def my_reservations(request):
    Reservation.objects.expire_overdue()
    if request.method == "GET":
        qs = _queryset().filter(user=request.user)[:50]
        return Response(ReservationSerializer(qs, many=True).data)

    data = ReservationCreateSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    qty = data.validated_data["quantity"]

    # Bir vaqtda ikki kishi oxirgi donani bron qilmasligi uchun qatorni qulflaymiz
    with transaction.atomic():
        inv = get_object_or_404(Inventory.objects.select_for_update().select_related("medicine", "pharmacy"),
                                pk=data.validated_data["inventory_id"])
        if not inv.pharmacy.is_open_now():
            return Response({"detail": msg(request, "closed")}, status=status.HTTP_400_BAD_REQUEST)
        if inv.available_quantity < qty:
            return Response({"detail": msg(request, "only_left", n=inv.available_quantity)},
                            status=status.HTTP_409_CONFLICT)
        try:
            lat, lng = float(request.data.get("lat")), float(request.data.get("lng"))
        except (TypeError, ValueError):
            lat = lng = None
        res = Reservation.objects.create(
            user=request.user, inventory=inv, quantity=qty, code=f"{secrets.randbelow(10000):04d}",
            hold_minutes=hold_minutes_for(inv.pharmacy, lat, lng),
        )
    return Response(ReservationSerializer(res).data, status=status.HTTP_201_CREATED)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def cancel_reservation(request, pk: int):
    res = get_object_or_404(Reservation, pk=pk, user=request.user)
    if res.status not in (Reservation.Status.PENDING, Reservation.Status.CONFIRMED):
        return Response({"detail": msg(request, "cannot_cancel")}, status=status.HTTP_400_BAD_REQUEST)
    res.status = Reservation.Status.CANCELLED
    res.save(update_fields=["status"])
    return Response(ReservationSerializer(res).data)
