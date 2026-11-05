from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone


def notify(user, kind, **data):
    from .models import Notification
    return Notification.objects.create(user=user, kind=kind, data=data)


def notify_back_in_stock(inventory):
    """Dorixonada dori 0 dan ko'paydi — kuzatayotgan mijozlarga xabar."""
    from django.db.models import Q

    from .models import StockWatch
    watches = StockWatch.objects.filter(medicine_id=inventory.medicine_id, notified_at__isnull=True).filter(
        Q(pharmacy__isnull=True) | Q(pharmacy_id=inventory.pharmacy_id)).select_related("user")
    now = timezone.now()
    for w in watches:
        notify(w.user, "back_in_stock", medicine=str(inventory.medicine), medicine_id=inventory.medicine_id,
               pharmacy=inventory.pharmacy.name, quantity=inventory.quantity)
        w.notified_at = now
        w.save(update_fields=["notified_at"])


def award_cashback(order):
    """Buyurtma yakunlanganda keshbek: dorilar summasining CASHBACK_PERCENT foizi."""
    from apps.accounts.models import User
    if order.points_earned:
        return 0
    paid_items = max(0, order.items_total - order.points_used)
    pts = paid_items * settings.CASHBACK_PERCENT // 100
    if pts <= 0:
        return 0
    with transaction.atomic():
        User.objects.filter(pk=order.user_id).update(points=F("points") + pts)
        order.points_earned = pts
        order.save(update_fields=["points_earned"])
    notify(order.user, "points", points=pts, order_id=order.id)
    return pts
