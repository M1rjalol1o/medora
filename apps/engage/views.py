from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.i18n import msg
from apps.catalog.models import Medicine

from .models import Notification, StockWatch

S = extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)


def watch_dict(w):
    return {"id": w.id, "medicine": {"id": w.medicine_id, "name": str(w.medicine)},
            "pharmacy": w.pharmacy.name if w.pharmacy_id else None,
            "created_at": w.created_at, "notified_at": w.notified_at}


def notif_dict(n):
    return {"id": n.id, "kind": n.kind, "data": n.data, "is_read": n.is_read, "created_at": n.created_at}


@S
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def watches(request):
    """'Paydo bo'lsa xabar ber'. POST {medicine_id, pharmacy_id?}"""
    if request.method == "POST":
        med = get_object_or_404(Medicine, pk=request.data.get("medicine_id"))
        w, _ = StockWatch.objects.get_or_create(user=request.user, medicine=med,
                                                pharmacy_id=request.data.get("pharmacy_id") or None,
                                                notified_at__isnull=True)
        return Response(watch_dict(w), status=201)
    qs = StockWatch.objects.filter(user=request.user).select_related("medicine", "pharmacy")[:30]
    return Response([watch_dict(w) for w in qs])


@S
@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def watch_detail(request, pk):
    StockWatch.objects.filter(user=request.user, medicine_id=pk, notified_at__isnull=True).delete()
    return Response(status=204)


@S
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def notifications(request):
    qs = Notification.objects.filter(user=request.user)
    return Response({"unread": qs.filter(is_read=False).count(), "items": [notif_dict(n) for n in qs[:40]]})


@S
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({"ok": True})


@S
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def home(request):
    """Bosh sahifa uchun hammasi bitta so'rovda: keyingi dori, faol buyurtma, bron, ballar, xabarlar."""
    from apps.orders.models import Order
    from apps.orders.services import expire_unpaid
    from apps.reservations.models import Reservation

    u = request.user
    expire_unpaid()
    Reservation.objects.expire_overdue()
    now = timezone.localtime()
    today, hm = now.date(), now.strftime("%H:%M")

    # Keyingi qabul (bugun, hali ichilmagan)
    next_dose = None
    for c in u.courses.filter(is_active=True, end_date__gte=today, start_date__lte=today).select_related("member"):
        done = set(c.logs.filter(date=today).values_list("time", flat=True))
        for t in c.times:
            if t >= hm and t not in done and (next_dose is None or t < next_dose["time"]):
                next_dose = {"course_id": c.id, "medicine_name": c.medicine_name, "dose": c.dose, "time": t,
                             "member": c.member.name if c.member_id else None}

    o = Order.objects.filter(user=u).exclude(status__in=["completed", "cancelled"]).first()
    active_order = None
    if o:
        d = getattr(o, "delivery", None)
        active_order = {"id": o.id, "status": o.status, "total": o.total, "fulfillment": o.fulfillment,
                        "pharmacies": o.pharmacy_orders.count(),
                        "driver": (d.driver.user.first_name or d.driver.user.username) if d and d.driver_id else None,
                        "car": f"{d.driver.car_model} · {d.driver.car_number}" if d and d.driver_id else None}

    res = [{"id": r.id, "medicine": str(r.inventory.medicine), "pharmacy": r.inventory.pharmacy.name,
            "code": r.code, "expires_at": r.expires_at}
           for r in Reservation.objects.active().filter(user=u).select_related("inventory__medicine",
                                                                              "inventory__pharmacy")[:3]]
    return Response({
        "name": u.first_name or u.username, "points": u.points,
        "unread": Notification.objects.filter(user=u, is_read=False).count(),
        "next_dose": next_dose, "active_order": active_order, "reservations": res,
        "watching": StockWatch.objects.filter(user=u, notified_at__isnull=True).count(),
    })
