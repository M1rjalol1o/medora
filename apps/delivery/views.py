"""Haydovchi va taksopark API."""
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.i18n import msg
from apps.accounts.permissions import IsDriver, IsTaxiPark
from apps.orders.models import Order, PharmacyOrder
from apps.orders.serializers import delivery_dict, driver_dict
from apps.orders.services import record_sales, sync_order_status
from apps.payments.models import Payment
from apps.search.geo import haversine_km

from .models import Delivery, DeliveryStop, Driver

S = extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
ACTIVE = [Delivery.Status.ASSIGNED, Delivery.Status.PICKING, Delivery.Status.DELIVERING]


def task_dict(d, driver=None):
    data = delivery_dict(d)
    o = d.order
    data.update({
        "order_id": o.id, "payment_method": o.payment_method, "is_paid": o.is_paid,
        "collect_cash": o.total if (o.payment_method == "cash" and not o.is_paid) else 0,
        "customer": {"name": o.user.first_name or o.user.username, "phone": o.user.phone, "address": o.address},
        "pharmacy_orders": [{"id": po.id, "pharmacy": po.pharmacy.name, "status": po.status,
                             "items": [f"{i.medicine_name} × {i.quantity}" for i in po.items.all()]}
                            for po in o.pharmacy_orders.all() if po.status != "rejected"],
        "created_at": d.created_at,
    })
    if driver and driver.lat is not None and d.stops.exists():
        s = d.stops.first()
        data["to_first_stop_km"] = round(haversine_km(driver.lat, driver.lng, s.lat, s.lng), 2)
    return data


def dqs():
    return Delivery.objects.select_related("order__user", "driver__user", "driver__park").prefetch_related(
        "stops", "order__pharmacy_orders__items", "order__pharmacy_orders__pharmacy")


def finish_earnings(d):
    platform = d.fee * settings.PLATFORM_COMMISSION_PERCENT // 100
    park = d.fee * (d.park.commission_percent if d.park else 0) // 100
    d.platform_earning, d.park_earning, d.driver_earning = platform, park, d.fee - platform - park


# ---------------- Haydovchi ----------------
@S
@api_view(["GET"])
@permission_classes([IsDriver])
def driver_me(request):
    dr = request.user.driver_profile
    today = timezone.localdate()
    done = dr.deliveries.filter(status=Delivery.Status.DELIVERED)
    return Response({
        "driver": driver_dict(dr), "is_online": dr.is_online,
        "today_earning": done.filter(delivered_at__date=today).aggregate(s=Sum("driver_earning"))["s"] or 0,
        "today_count": done.filter(delivered_at__date=today).count(),
        "total_earning": done.aggregate(s=Sum("driver_earning"))["s"] or 0,
        "cash_on_hand": done.filter(order__payment_method="cash", cash_collected=True,
                                    delivered_at__date=today).aggregate(s=Sum("order__total"))["s"] or 0,
    })


@S
@api_view(["POST"])
@permission_classes([IsDriver])
def driver_online(request):
    dr = request.user.driver_profile
    dr.is_online = bool(request.data.get("is_online"))
    dr.save(update_fields=["is_online"])
    return Response({"is_online": dr.is_online})


@S
@api_view(["POST"])
@permission_classes([IsDriver])
def driver_location(request):
    dr = request.user.driver_profile
    try:
        dr.lat, dr.lng = float(request.data["lat"]), float(request.data["lng"])
    except (KeyError, TypeError, ValueError):
        return Response({"detail": msg(request, "bad_value", f="lat/lng")}, status=400)
    dr.location_updated_at = timezone.now()
    dr.save(update_fields=["lat", "lng", "location_updated_at"])
    return Response({"ok": True})


@S
@api_view(["GET"])
@permission_classes([IsDriver])
def driver_available(request):
    dr = request.user.driver_profile
    qs = dqs().filter(status=Delivery.Status.SEARCHING, driver__isnull=True).exclude(
        order__status__in=[Order.Status.AWAITING_PAYMENT, Order.Status.CANCELLED])
    tasks = [task_dict(d, dr) for d in qs[:30]]
    tasks.sort(key=lambda t: t.get("to_first_stop_km", 0))
    return Response(tasks)


@S
@api_view(["GET"])
@permission_classes([IsDriver])
def driver_current(request):
    d = dqs().filter(driver=request.user.driver_profile, status__in=ACTIVE).first()
    return Response(task_dict(d) if d else None)


@S
@api_view(["GET"])
@permission_classes([IsDriver])
def driver_history(request):
    qs = dqs().filter(driver=request.user.driver_profile, status=Delivery.Status.DELIVERED)[:50]
    return Response([task_dict(d) for d in qs])


@S
@api_view(["POST"])
@permission_classes([IsDriver])
def driver_accept(request, pk):
    dr = request.user.driver_profile
    if not dr.is_online:
        return Response({"detail": msg(request, "offline")}, status=400)
    if Delivery.objects.filter(driver=dr, status__in=ACTIVE).exists():
        return Response({"detail": msg(request, "has_active")}, status=400)
    with transaction.atomic():
        d = get_object_or_404(Delivery.objects.select_for_update(), pk=pk)
        if d.driver_id or d.status != Delivery.Status.SEARCHING:
            return Response({"detail": msg(request, "delivery_taken")}, status=409)
        d.driver, d.park, d.status, d.assigned_at = dr, dr.park, Delivery.Status.ASSIGNED, timezone.now()
        d.save()
    return Response(task_dict(dqs().get(pk=pk)))


@S
@api_view(["POST"])
@permission_classes([IsDriver])
def driver_stop_done(request, pk):
    """Nuqtani bajarish. pickup — dorixona tayyorlagan bo'lishi kerak. dropoff — mijoz kodi."""
    dr = request.user.driver_profile
    with transaction.atomic():
        stop = get_object_or_404(DeliveryStop.objects.select_for_update().select_related("delivery__order"),
                                 pk=pk, delivery__driver=dr)
        d, order = stop.delivery, stop.delivery.order
        if stop.done_at or d.status not in ACTIVE:
            return Response({"detail": msg(request, "bad_status")}, status=400)
        prev_open = d.stops.filter(sequence__lt=stop.sequence, done_at__isnull=True)
        if stop.kind == "pickup":
            po = stop.pharmacy_order
            if po.status == PharmacyOrder.Status.REJECTED:
                pass                                  # rad etilgan dorixona — o'tkazib yuboriladi
            elif po.status != PharmacyOrder.Status.READY:
                return Response({"detail": msg(request, "not_ready")}, status=400)
            else:
                po.status = PharmacyOrder.Status.PICKED_UP
                po.save(update_fields=["status", "updated_at"])
                record_sales(po)
            stop.done_at = timezone.now()
            stop.save(update_fields=["done_at"])
            remaining = d.stops.filter(kind="pickup", done_at__isnull=True).exists()
            d.status = Delivery.Status.PICKING if remaining else Delivery.Status.DELIVERING
            d.save(update_fields=["status"])
        else:
            if prev_open.exists():
                return Response({"detail": msg(request, "bad_status")}, status=400)
            if str(request.data.get("code", "")) != order.delivery_code:
                return Response({"detail": msg(request, "wrong_code")}, status=400)
            stop.done_at = timezone.now()
            stop.save(update_fields=["done_at"])
            d.status, d.delivered_at = Delivery.Status.DELIVERED, timezone.now()
            finish_earnings(d)
            if order.payment_method == "cash":
                d.cash_collected = True
                order.is_paid = True
                order.save(update_fields=["is_paid"])
                order.payments.filter(status=Payment.Status.CASH_PENDING).update(
                    status=Payment.Status.PAID, paid_at=timezone.now())
            d.save()
    sync_order_status(order)
    return Response(task_dict(dqs().get(pk=d.pk)))


# ---------------- Taksopark ----------------
@S
@api_view(["GET"])
@permission_classes([IsTaxiPark])
def park_dashboard(request):
    park = request.user.taxi_park
    today = timezone.localdate()
    dl = Delivery.objects.filter(park=park)
    done_today = dl.filter(status=Delivery.Status.DELIVERED, delivered_at__date=today)
    return Response({
        "park": {"id": park.id, "name": park.name, "commission_percent": park.commission_percent},
        "drivers_total": park.drivers.count(),
        "drivers_online": park.drivers.filter(is_online=True).count(),
        "active_deliveries": dl.filter(status__in=ACTIVE).count(),
        "today_deliveries": done_today.count(),
        "today_turnover": done_today.aggregate(s=Sum("fee"))["s"] or 0,
        "today_park_earning": done_today.aggregate(s=Sum("park_earning"))["s"] or 0,
        "waiting_in_city": Delivery.objects.filter(status=Delivery.Status.SEARCHING).exclude(
            order__status__in=["awaiting_payment", "cancelled"]).count(),
    })


@S
@api_view(["GET"])
@permission_classes([IsTaxiPark])
def park_drivers(request):
    park = request.user.taxi_park
    today = timezone.localdate()
    rows = []
    for dr in park.drivers.select_related("user").annotate(
            done=Count("deliveries", filter=Q(deliveries__status="delivered", deliveries__delivered_at__date=today)),
            earn=Sum("deliveries__driver_earning", filter=Q(deliveries__status="delivered",
                                                             deliveries__delivered_at__date=today))):
        active = dr.deliveries.filter(status__in=ACTIVE).first()
        rows.append({**driver_dict(dr), "is_online": dr.is_online, "today_done": dr.done,
                     "today_earning": dr.earn or 0, "busy": bool(active),
                     "active_order": active.order_id if active else None})
    rows.sort(key=lambda r: (not r["is_online"], r["busy"]))
    return Response(rows)


@S
@api_view(["GET"])
@permission_classes([IsTaxiPark])
def park_deliveries(request):
    park = request.user.taxi_park
    mine = dqs().filter(park=park)[:50]
    waiting = dqs().filter(status=Delivery.Status.SEARCHING).exclude(
        order__status__in=["awaiting_payment", "cancelled"])[:30]
    return Response({"waiting": [task_dict(d) for d in waiting], "mine": [task_dict(d) for d in mine]})


@S
@api_view(["POST"])
@permission_classes([IsTaxiPark])
def park_assign(request, pk):
    """Dispetcher: kutilayotgan yetkazishni o'z haydovchisiga biriktirish. body {driver_id}"""
    park = request.user.taxi_park
    dr = get_object_or_404(Driver, pk=request.data.get("driver_id"), park=park)
    if not dr.is_online:
        return Response({"detail": msg(request, "offline")}, status=400)
    if Delivery.objects.filter(driver=dr, status__in=ACTIVE).exists():
        return Response({"detail": msg(request, "has_active")}, status=400)
    with transaction.atomic():
        d = get_object_or_404(Delivery.objects.select_for_update(), pk=pk)
        if d.driver_id or d.status != Delivery.Status.SEARCHING:
            return Response({"detail": msg(request, "delivery_taken")}, status=409)
        d.driver, d.park, d.status, d.assigned_at = dr, park, Delivery.Status.ASSIGNED, timezone.now()
        d.save()
    return Response(task_dict(dqs().get(pk=pk)))
