"""Buyurtma yaratish, marshrut va narx, holatlarni sinxronlash."""
import secrets
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.delivery.models import Delivery, DeliveryStop
from apps.payments.models import Payment
from apps.pharmacies.models import Inventory, SaleRecord
from apps.search.geo import haversine_km


class OrderError(Exception):
    def __init__(self, key, **kw):
        self.key, self.kw = key, kw


def code4() -> str:
    return f"{secrets.randbelow(10000):04d}"


def plan_route(pharmacies, dest_lat, dest_lng):
    """Dorixonalar tartibi: mijozdan eng uzoq dorixonadan boshlab, eng yaqin qo'shniga o'tib, mijozga.
    (Kichik sondagi nuqtalar uchun yetarli; keyin route optimization API bilan almashtiriladi.)"""
    left = list(pharmacies)
    if not left:
        return [], 0.0
    current = max(left, key=lambda p: haversine_km(p.lat, p.lng, dest_lat, dest_lng))
    route, dist = [current], 0.0
    left.remove(current)
    while left:
        nxt = min(left, key=lambda p: haversine_km(current.lat, current.lng, p.lat, p.lng))
        dist += haversine_km(current.lat, current.lng, nxt.lat, nxt.lng)
        route.append(nxt)
        left.remove(nxt)
        current = nxt
    dist += haversine_km(current.lat, current.lng, dest_lat, dest_lng)
    return route, dist * 1.35          # yo'l koeffitsienti


def delivery_fee(distance_km: float, stops: int) -> int:
    fee = settings.DELIVERY_BASE_FEE + settings.DELIVERY_PER_KM * distance_km \
        + settings.DELIVERY_PER_EXTRA_STOP * max(0, stops - 1)
    return int(round(fee / 500.0)) * 500


def quote(items, fulfillment, lat, lng):
    """Savat narxi va yetkazish narxini hisoblaydi (buyurtma yaratmasdan)."""
    invs = {i.id: i for i in Inventory.objects.select_related("pharmacy", "medicine")
            .filter(id__in=[x["inventory_id"] for x in items])}
    groups = defaultdict(int)
    for x in items:
        inv = invs.get(x["inventory_id"])
        if inv:
            groups[inv.pharmacy] += inv.final_price * int(x["quantity"])
    items_total = sum(groups.values())
    fee, dist = 0, 0.0
    if fulfillment == "delivery" and groups and lat is not None:
        _, dist = plan_route(list(groups.keys()), lat, lng)
        fee = delivery_fee(dist, len(groups))
    return {"items_total": items_total, "delivery_fee": fee, "distance_km": round(dist, 2),
            "pharmacies": len(groups), "total": items_total + fee}


@transaction.atomic
def create_order(user, items, fulfillment, payment_method, address="", lat=None, lng=None,
                 prescription=None, comment=""):
    from .models import Order, OrderItem, PharmacyOrder
    if not items:
        raise OrderError("empty_cart")
    ids = [int(x["inventory_id"]) for x in items]
    invs = {i.id: i for i in Inventory.objects.select_for_update().select_related("pharmacy", "medicine").filter(id__in=ids)}

    by_pharmacy = defaultdict(list)
    for x in items:
        inv = invs.get(int(x["inventory_id"]))
        qty = int(x["quantity"])
        if not inv or qty < 1:
            raise OrderError("not_found")
        if not inv.pharmacy.is_open_now():
            raise OrderError("closed")
        if inv.available_quantity < qty:
            raise OrderError("only_left", n=inv.available_quantity)
        if inv.medicine.requires_prescription and prescription is None:
            raise OrderError("rx_required")
        by_pharmacy[inv.pharmacy].append((inv, qty))

    order = Order.objects.create(
        user=user, fulfillment=fulfillment, payment_method=payment_method, address=address,
        lat=lat, lng=lng, comment=comment, prescription=prescription, delivery_code=code4(),
        status=Order.Status.AWAITING_PAYMENT if payment_method == "card" else Order.Status.CONFIRMED,
    )
    items_total = 0
    for ph, lines in by_pharmacy.items():
        po = PharmacyOrder.objects.create(order=order, pharmacy=ph, pickup_code=code4())
        sub = 0
        for inv, qty in lines:
            price = inv.final_price
            OrderItem.objects.create(pharmacy_order=po, inventory=inv, medicine_name=str(inv.medicine),
                                     quantity=qty, price=price, requires_prescription=inv.medicine.requires_prescription)
            inv.quantity -= qty                       # zaxira darhol band qilinadi
            inv.save(update_fields=["quantity", "updated_at"])
            sub += price * qty
        po.subtotal = sub
        po.save(update_fields=["subtotal"])
        items_total += sub

    fee, dist = 0, 0.0
    if fulfillment == "delivery":
        route, dist = plan_route(list(by_pharmacy.keys()), lat, lng)
        fee = delivery_fee(dist, len(route))
        delivery = Delivery.objects.create(order=order, fee=fee, distance_km=round(dist, 2))
        pos = {po.pharmacy_id: po for po in order.pharmacy_orders.all()}
        for i, ph in enumerate(route, start=1):
            DeliveryStop.objects.create(delivery=delivery, sequence=i, kind="pickup", pharmacy_order=pos[ph.id],
                                        title=ph.name, address=ph.address, lat=ph.lat, lng=ph.lng)
        DeliveryStop.objects.create(delivery=delivery, sequence=len(route) + 1, kind="dropoff",
                                    title=user.first_name or user.username, address=address, lat=lat, lng=lng)

    order.items_total, order.delivery_fee, order.total = items_total, fee, items_total + fee
    order.save(update_fields=["items_total", "delivery_fee", "total"])
    Payment.objects.create(order=order, amount=order.total, method=payment_method,
                           status=Payment.Status.PENDING if payment_method == "card" else Payment.Status.CASH_PENDING)
    return order


def restore_stock(pharmacy_order):
    for it in pharmacy_order.items.select_related("inventory"):
        inv = Inventory.objects.select_for_update().get(pk=it.inventory_id)
        inv.quantity += it.quantity
        inv.save(update_fields=["quantity", "updated_at"])


def record_sales(pharmacy_order):
    """Sotuv tarixiga yozish — bashorat modeli shundan o'rganadi."""
    now = timezone.localtime()
    for it in pharmacy_order.items.select_related("inventory"):
        SaleRecord.objects.create(pharmacy_id=pharmacy_order.pharmacy_id, medicine_id=it.inventory.medicine_id,
                                  date=now.date(), hour=now.hour, quantity=it.quantity)


@transaction.atomic
def cancel_order(order, reason_refund=True):
    from .models import Order, PharmacyOrder
    for po in order.pharmacy_orders.select_for_update():
        if po.status in (PharmacyOrder.Status.NEW, PharmacyOrder.Status.ACCEPTED, PharmacyOrder.Status.READY):
            restore_stock(po)
            po.status = PharmacyOrder.Status.REJECTED
            po.save(update_fields=["status", "updated_at"])
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status"])
    if hasattr(order, "delivery"):
        order.delivery.status = Delivery.Status.CANCELLED
        order.delivery.save(update_fields=["status"])
    for p in order.payments.filter(status=Payment.Status.PAID):
        from apps.payments.provider import get_provider
        if reason_refund and get_provider().refund(p.provider_ref, p.amount):
            p.status = Payment.Status.REFUNDED
            p.save(update_fields=["status"])
    order.payments.filter(status__in=[Payment.Status.PENDING, Payment.Status.CASH_PENDING]).update(status=Payment.Status.FAILED)


def expire_unpaid():
    """To'lanmagan karta buyurtmalarini bekor qilib, zaxirani qaytaradi."""
    from .models import Order
    limit = timezone.now() - timedelta(minutes=settings.ORDER_PAYMENT_TIMEOUT_MINUTES)
    for order in Order.objects.filter(status=Order.Status.AWAITING_PAYMENT, created_at__lt=limit):
        cancel_order(order, reason_refund=False)


def sync_order_status(order):
    """Sub-buyurtmalar va yetkazish holatidan umumiy holatni chiqaradi."""
    from .models import Order, PharmacyOrder
    if order.status in (Order.Status.CANCELLED, Order.Status.COMPLETED, Order.Status.AWAITING_PAYMENT):
        return
    sts = [po.status for po in order.pharmacy_orders.all() if po.status != PharmacyOrder.Status.REJECTED]
    if not sts:
        cancel_order(order)
        return
    new = order.status
    if order.fulfillment == "pickup":
        if all(s == "issued" for s in sts):
            new = Order.Status.COMPLETED
        elif all(s in ("ready", "issued") for s in sts):
            new = Order.Status.READY
        elif any(s != "new" for s in sts):
            new = Order.Status.PREPARING
    else:
        d = getattr(order, "delivery", None)
        if d and d.status == Delivery.Status.DELIVERED:
            new = Order.Status.COMPLETED
        elif d and d.status == Delivery.Status.DELIVERING:
            new = Order.Status.DELIVERING
        elif all(s in ("ready", "picked_up") for s in sts):
            new = Order.Status.READY
        elif any(s != "new" for s in sts):
            new = Order.Status.PREPARING
    if new != order.status:
        order.status = new
        order.save(update_fields=["status"])
