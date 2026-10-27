"""Dorixona paneli: ombor, tugash prognozi, bronlar."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsPharmacyStaff
from apps.pharmacies.models import Inventory, SaleRecord
from apps.reservations.models import Reservation
from apps.reservations.serializers import ReservationSerializer
from apps.search.prediction import hourly_rates, hours_until_stockout


def _rates_for(pharmacy_id, medicine_ids):
    """Har bir dori uchun shu dorixonadagi sotuv tezligi."""
    out = {}
    for mid in medicine_ids:
        out[mid] = hourly_rates(mid, [pharmacy_id]).get(pharmacy_id, 0)
    return out


def _inventory_rows(pharmacy):
    items = list(Inventory.objects.filter(pharmacy=pharmacy).select_related("medicine"))
    rates = _rates_for(pharmacy.id, [i.medicine_id for i in items])
    rows = []
    for inv in items:
        avail = inv.available_quantity
        rate = rates.get(inv.medicine_id, 0)
        hrs = hours_until_stockout(avail, rate)
        if avail == 0:
            level = "out"
        elif (hrs is not None and hrs < 6) or avail <= inv.min_stock:
            level = "low"
        else:
            level = "ok"
        rows.append({
            "id": inv.id,
            "medicine": {"id": inv.medicine_id, "name": inv.medicine.name, "dosage": inv.medicine.dosage,
                         "form": inv.medicine.form},
            "quantity": inv.quantity,
            "reserved": inv.quantity - avail,
            "available": avail,
            "price": int(inv.price),
            "final_price": inv.final_price,
            "discount_percent": inv.discount_percent,
            "expiry_date": inv.expiry_date,
            "days_to_expiry": inv.days_to_expiry,
            "min_stock": inv.min_stock,
            "sales_per_hour": round(rate, 2),
            "hours_until_stockout": round(hrs, 1) if hrs is not None else None,
            "level": level,
            "updated_at": inv.updated_at,
        })
    order = {"out": 0, "low": 1, "ok": 2}
    rows.sort(key=lambda r: (order[r["level"]], r["hours_until_stockout"] or 1e9))
    return rows


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsPharmacyStaff])
def dashboard(request):
    ph = request.user.pharmacy
    Reservation.objects.expire_overdue()
    rows = _inventory_rows(ph)
    today = timezone.localdate()
    sold_today = sum(SaleRecord.objects.filter(pharmacy=ph, date=today).values_list("quantity", flat=True))
    active = Reservation.objects.active().filter(inventory__pharmacy=ph).count()
    from django.conf import settings as dj
    from apps.orders.models import PharmacyOrder
    new_orders = PharmacyOrder.objects.filter(pharmacy=ph, status__in=["new", "accepted"]).exclude(
        order__status__in=["awaiting_payment", "cancelled"]).count()
    expiring = sum(1 for r in rows if r["days_to_expiry"] is not None and r["days_to_expiry"] <= dj.EXPIRING_SOON_DAYS
                   and r["quantity"] > 0)
    return Response({
        "pharmacy": {"id": ph.id, "name": ph.name, "address": ph.address},
        "active_reservations": active,
        "new_orders": new_orders,
        "expiring": expiring,
        "sold_today": sold_today,
        "out_of_stock": sum(1 for r in rows if r["level"] == "out"),
        "low_stock": sum(1 for r in rows if r["level"] == "low"),
        "alerts": [r for r in rows if r["level"] != "ok"][:8],
    })


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsPharmacyStaff])
def inventory_list(request):
    Reservation.objects.expire_overdue()
    return Response(_inventory_rows(request.user.pharmacy))


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(["PATCH"])
@permission_classes([IsPharmacyStaff])
def inventory_update(request, pk: int):
    """Qoldiq yoki narxni yangilash (faqat o'z dorixonasi)."""
    inv = get_object_or_404(Inventory, pk=pk, pharmacy=request.user.pharmacy)
    for field in ("quantity", "price", "min_stock", "discount_percent"):
        if field in request.data:
            try:
                value = int(request.data[field])
            except (TypeError, ValueError):
                return Response({"detail": f"{field} noto'g'ri"}, status=status.HTTP_400_BAD_REQUEST)
            if value < 0 or (field == "discount_percent" and value > 90):
                return Response({"detail": f"{field} manfiy bo'lishi mumkin emas"}, status=status.HTTP_400_BAD_REQUEST)
            setattr(inv, field, value)
    inv.save()
    return Response({"id": inv.id, "quantity": inv.quantity, "price": int(inv.price), "min_stock": inv.min_stock,
                     "discount_percent": inv.discount_percent})


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsPharmacyStaff])
def reservation_list(request):
    Reservation.objects.expire_overdue()
    qs = (Reservation.objects.select_related("inventory__medicine", "inventory__pharmacy", "user")
          .filter(inventory__pharmacy=request.user.pharmacy)[:100])
    return Response(ReservationSerializer(qs, many=True).data)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(["POST"])
@permission_classes([IsPharmacyStaff])
def reservation_action(request, pk: int, action: str):
    """confirm — tasdiqlash, complete — mijozga berish (kod bilan), cancel — bekor qilish."""
    Reservation.objects.expire_overdue()
    with transaction.atomic():
        res = get_object_or_404(Reservation.objects.select_for_update().select_related("inventory"),
                                pk=pk, inventory__pharmacy=request.user.pharmacy)
        active = (Reservation.Status.PENDING, Reservation.Status.CONFIRMED)
        if res.status not in active:
            return Response({"detail": f"Bron holati: {res.get_status_display()}"}, status=status.HTTP_400_BAD_REQUEST)

        if action == "confirm":
            res.status = Reservation.Status.CONFIRMED
        elif action == "cancel":
            res.status = Reservation.Status.CANCELLED
        elif action == "complete":
            if str(request.data.get("code", "")) != res.code:
                return Response({"detail": "Kod noto'g'ri."}, status=status.HTTP_400_BAD_REQUEST)
            inv = Inventory.objects.select_for_update().get(pk=res.inventory_id)
            inv.quantity = max(0, inv.quantity - res.quantity)
            inv.save(update_fields=["quantity", "updated_at"])
            now = timezone.localtime()
            SaleRecord.objects.create(pharmacy_id=inv.pharmacy_id, medicine_id=inv.medicine_id,
                                      date=now.date(), hour=now.hour, quantity=res.quantity)
            res.status = Reservation.Status.COMPLETED
        else:
            return Response({"detail": "Noma'lum amal"}, status=status.HTTP_400_BAD_REQUEST)
        res.save(update_fields=["status"])
    res.refresh_from_db()
    return Response(ReservationSerializer(res).data)


# ---------- Muddati yaqin dorilar ----------
@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsPharmacyStaff])
def expiring(request):
    """?days=90 — muddati shu kun ichida tugaydigan dorilar (eng yaqini birinchi) + tavsiya chegirma."""
    from django.conf import settings as dj
    try:
        days = int(request.GET.get("days", dj.EXPIRING_SOON_DAYS))
    except ValueError:
        days = dj.EXPIRING_SOON_DAYS
    rows = []
    for r in _inventory_rows(request.user.pharmacy):
        d = r["days_to_expiry"]
        if d is None or d > days or r["quantity"] == 0:
            continue
        # Sotuv tezligi bo'yicha muddatgacha sotilib ulguradimi?
        sell_days = (r["quantity"] / (r["sales_per_hour"] * 14)) if r["sales_per_hour"] else None
        at_risk = max(0, r["quantity"] - int(r["sales_per_hour"] * 14 * max(d, 0))) if r["sales_per_hour"] else r["quantity"]
        # Muddatgacha baribir sotilib ketsa — chegirma shart emas
        suggested = 0 if at_risk == 0 else 10 if d > 60 else 20 if d > 30 else 30 if d > 14 else 50
        rows.append({**r, "expired": d < 0, "days_to_sell_out": round(sell_days, 1) if sell_days else None,
                     "units_at_risk": at_risk, "loss_at_risk": at_risk * r["price"], "suggested_discount": suggested})
    rows.sort(key=lambda r: r["days_to_expiry"])
    return Response({"days": days, "items": rows,
                     "total_units_at_risk": sum(r["units_at_risk"] for r in rows),
                     "total_loss_at_risk": sum(r["loss_at_risk"] for r in rows)})


# ---------- Buyurtmalar (bir nechta dorixonali buyurtmaning shu dorixonaga tegishli qismi) ----------
def _po_dict(request, po):
    o = po.order
    return {
        "id": po.id, "order_id": o.id, "status": po.status, "subtotal": po.subtotal, "pickup_code": None,
        "fulfillment": o.fulfillment, "payment_method": o.payment_method, "is_paid": o.is_paid,
        "customer": o.user.first_name or o.user.username, "customer_phone": o.user.phone,
        "items": [{"name": i.medicine_name, "quantity": i.quantity, "price": i.price, "rx": i.requires_prescription}
                  for i in po.items.all()],
        "has_rx": any(i.requires_prescription for i in po.items.all()),
        "prescription_image": request.build_absolute_uri(o.prescription.image.url)
        if o.prescription_id and o.prescription.image else None,
        "prescription_text": o.prescription.raw_text if o.prescription_id else "",
        "rx_verified": po.rx_verified,
        "driver": (o.delivery.driver.user.first_name + " · " + o.delivery.driver.car_number)
        if o.fulfillment == "delivery" and hasattr(o, "delivery") and o.delivery.driver_id else None,
        "created_at": o.created_at,
    }


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsPharmacyStaff])
def pharmacy_orders(request):
    from apps.orders.models import PharmacyOrder
    from apps.orders.services import expire_unpaid
    expire_unpaid()
    qs = (PharmacyOrder.objects.filter(pharmacy=request.user.pharmacy)
          .exclude(order__status="awaiting_payment")
          .select_related("order__user", "order__prescription", "order__delivery__driver__user")
          .prefetch_related("items").order_by("-order__created_at")[:80])
    return Response([_po_dict(request, po) for po in qs])


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(["POST"])
@permission_classes([IsPharmacyStaff])
def pharmacy_order_action(request, pk, action):
    """accept / ready / reject / issue (o'zi olib ketganda kod bilan) / verify_rx"""
    from apps.accounts.i18n import msg
    from apps.orders.models import PharmacyOrder
    from apps.orders.services import record_sales, restore_stock, sync_order_status
    from apps.payments.models import Payment
    from apps.payments.provider import get_provider
    with transaction.atomic():
        po = get_object_or_404(PharmacyOrder.objects.select_for_update().select_related("order"),
                               pk=pk, pharmacy=request.user.pharmacy)
        o = po.order
        if o.status in ("awaiting_payment", "cancelled"):
            return Response({"detail": msg(request, "bad_status")}, status=400)
        flow = {"accept": ("new",), "ready": ("new", "accepted"), "reject": ("new", "accepted", "ready"),
                "issue": ("ready",), "verify_rx": ("new", "accepted", "ready")}
        if action not in flow:
            return Response({"detail": msg(request, "unknown_action")}, status=400)
        if po.status not in flow[action]:
            return Response({"detail": msg(request, "bad_status")}, status=400)
        if action == "verify_rx":
            po.rx_verified = True
        elif action == "accept":
            po.status = "accepted"
        elif action == "ready":
            has_rx = po.items.filter(requires_prescription=True).exists()
            if has_rx and not po.rx_verified:
                return Response({"detail": msg(request, "rx_required")}, status=400)
            po.status = "ready"
        elif action == "issue":
            if o.fulfillment != "pickup":
                return Response({"detail": msg(request, "bad_status")}, status=400)
            if str(request.data.get("code", "")) != po.pickup_code:
                return Response({"detail": msg(request, "wrong_code")}, status=400)
            po.status = "issued"
            record_sales(po)
            if o.payment_method == "cash" and not o.pharmacy_orders.exclude(pk=po.pk).exclude(
                    status__in=["issued", "rejected"]).exists():
                o.is_paid = True
                o.save(update_fields=["is_paid"])
                o.payments.filter(status="cash_pending").update(status="paid", paid_at=timezone.now())
        elif action == "reject":
            restore_stock(po)
            po.status = "rejected"
            # Umumiy summadan chiqariladi; karta bilan to'langan bo'lsa shu qism qaytariladi
            o.items_total -= po.subtotal
            o.total -= po.subtotal
            o.save(update_fields=["items_total", "total"])
            if o.is_paid and o.payment_method == "card":
                get_provider().refund("", po.subtotal)
                Payment.objects.create(order=o, amount=po.subtotal, method="card", status="refunded")
        po.save()
    sync_order_status(o)
    return Response({"ok": True, "status": po.status})
