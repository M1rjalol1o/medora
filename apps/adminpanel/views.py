"""Platforma administratori: hamma narsani ko'radi — mijozlar, dorixonalar, buyurtmalar, taksi va to'lovlar."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsPlatformAdmin
from apps.delivery.models import Delivery, Driver, TaxiPark
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
from apps.orders.views import order_qs
from apps.payments.models import Payment
from apps.pharmacies.models import Inventory, Pharmacy
from apps.reservations.models import Reservation

User = get_user_model()
S = extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
P = [IsPlatformAdmin]


@S
@api_view(["GET"])
@permission_classes(P)
def stats(request):
    today = timezone.localdate()
    week = [today - timedelta(days=i) for i in range(6, -1, -1)]
    paid = Payment.objects.filter(status="paid")
    by_day = {r["d"]: r for r in Order.objects.filter(created_at__date__gte=week[0]).exclude(status="cancelled")
              .values(d=TruncDate("created_at"))
              .annotate(n=Count("id"), s=Sum("total"))}
    return Response({
        "users": {r["role"]: r["n"] for r in User.objects.values("role").annotate(n=Count("id"))},
        "pharmacies": Pharmacy.objects.count(),
        "pharmacies_active": Pharmacy.objects.filter(is_active=True).count(),
        "taxi_parks": TaxiPark.objects.count(),
        "drivers_online": Driver.objects.filter(is_online=True).count(),
        "drivers_total": Driver.objects.count(),
        "orders_today": Order.objects.filter(created_at__date=today).count(),
        "orders_active": Order.objects.filter(status__in=["confirmed", "preparing", "ready", "delivering"]).count(),
        "deliveries_waiting": Delivery.objects.filter(status="searching").exclude(
            order__status__in=["awaiting_payment", "cancelled"]).count(),
        "reservations_active": Reservation.objects.active().count(),
        "revenue_today": paid.filter(paid_at__date=today).aggregate(s=Sum("amount"))["s"] or 0,
        "revenue_total": paid.aggregate(s=Sum("amount"))["s"] or 0,
        "platform_earning": Delivery.objects.filter(status="delivered").aggregate(s=Sum("platform_earning"))["s"] or 0,
        "out_of_stock_items": Inventory.objects.filter(quantity=0).count(),
        "week": [{"date": d, "orders": by_day.get(d, {}).get("n", 0), "revenue": by_day.get(d, {}).get("s") or 0}
                 for d in week],
    })


@S
@api_view(["GET"])
@permission_classes(P)
def users(request):
    qs = User.objects.select_related("pharmacy", "taxi_park").order_by("-date_joined")
    if request.GET.get("role"):
        qs = qs.filter(role=request.GET["role"])
    if request.GET.get("q"):
        q = request.GET["q"]
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(phone__icontains=q))
    qs = qs.annotate(n_orders=Count("orders", distinct=True))[:200]
    return Response([{"id": u.id, "username": u.username, "name": u.first_name, "phone": u.phone, "role": u.role,
                      "is_active": u.is_active, "pharmacy": u.pharmacy.name if u.pharmacy_id else None,
                      "taxi_park": u.taxi_park.name if u.taxi_park_id else None, "orders": u.n_orders,
                      "date_joined": u.date_joined} for u in qs])


@S
@api_view(["POST"])
@permission_classes(P)
def user_toggle(request, pk):
    u = get_object_or_404(User, pk=pk)
    if u == request.user:
        return Response({"detail": "self"}, status=400)
    u.is_active = not u.is_active
    u.save(update_fields=["is_active"])
    return Response({"id": u.id, "is_active": u.is_active})


@S
@api_view(["GET"])
@permission_classes(P)
def pharmacies(request):
    today = timezone.localdate()
    rows = []
    for p in Pharmacy.objects.annotate(
            items=Count("inventory", distinct=True),
            out=Count("inventory", filter=Q(inventory__quantity=0), distinct=True),
            orders_today=Count("orders", filter=Q(orders__order__created_at__date=today), distinct=True)):
        rows.append({"id": p.id, "name": p.name, "address": p.address, "phone": p.phone, "is_active": p.is_active,
                     "is_24h": p.is_24h, "items": p.items, "out_of_stock": p.out, "orders_today": p.orders_today,
                     "staff": p.staff.count()})
    return Response(rows)


@S
@api_view(["POST"])
@permission_classes(P)
def pharmacy_toggle(request, pk):
    p = get_object_or_404(Pharmacy, pk=pk)
    p.is_active = not p.is_active
    p.save(update_fields=["is_active"])
    return Response({"id": p.id, "is_active": p.is_active})


@S
@api_view(["GET"])
@permission_classes(P)
def orders(request):
    qs = order_qs()
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    return Response(OrderSerializer(qs[:100], many=True).data)


@S
@api_view(["GET"])
@permission_classes(P)
def taxi(request):
    today = timezone.localdate()
    parks = []
    for park in TaxiPark.objects.all():
        done = Delivery.objects.filter(park=park, status="delivered")
        parks.append({
            "id": park.id, "name": park.name, "phone": park.phone, "commission_percent": park.commission_percent,
            "is_active": park.is_active, "drivers": park.drivers.count(),
            "online": park.drivers.filter(is_online=True).count(),
            "today_deliveries": done.filter(delivered_at__date=today).count(),
            "turnover": done.aggregate(s=Sum("fee"))["s"] or 0,
        })
    drivers = [{"id": d.id, "name": d.user.first_name, "phone": d.user.phone, "park": d.park.name,
                "car": f"{d.car_model} · {d.car_number}", "is_online": d.is_online,
                "busy": d.deliveries.filter(status__in=["assigned", "picking", "delivering"]).exists(),
                "delivered": d.deliveries.filter(status="delivered").count()}
               for d in Driver.objects.select_related("user", "park")]
    return Response({"parks": parks, "drivers": drivers})


@S
@api_view(["GET"])
@permission_classes(P)
def payments(request):
    qs = Payment.objects.select_related("order__user", "card").order_by("-created_at")[:150]
    return Response([{"id": p.id, "order_id": p.order_id, "customer": p.order.user.first_name or p.order.user.username,
                      "amount": p.amount, "method": p.method, "status": p.status, "provider": p.provider,
                      "card": p.card.masked if p.card_id else None, "created_at": p.created_at} for p in qs])


@S
@api_view(["GET"])
@permission_classes(P)
def reservations(request):
    Reservation.objects.expire_overdue()
    qs = Reservation.objects.select_related("user", "inventory__medicine", "inventory__pharmacy")[:150]
    return Response([{"id": r.id, "customer": r.user.first_name or r.user.username, "medicine": str(r.inventory.medicine),
                      "pharmacy": r.inventory.pharmacy.name, "quantity": r.quantity, "status": r.status,
                      "hold_minutes": r.hold_minutes, "created_at": r.created_at, "expires_at": r.expires_at}
                     for r in qs])
