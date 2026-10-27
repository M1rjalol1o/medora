import re
import secrets
from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.i18n import msg
from apps.orders.models import Order
from apps.orders.services import sync_order_status

from .models import CardVerification, Payment, PaymentCard
from .provider import card_brand, get_provider, hash_otp, luhn_ok, mask

S = extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)


def card_dict(c):
    return {"id": c.id, "masked": c.masked, "brand": c.brand, "expiry": c.expiry}


@S
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def cards(request):
    """GET — saqlangan kartalar. POST {number, expiry} — kartani bog'lash (SMS kod yuboriladi)."""
    if request.method == "GET":
        return Response([card_dict(c) for c in request.user.cards.filter(is_active=True)])
    number = re.sub(r"\D", "", str(request.data.get("number", "")))
    expiry = str(request.data.get("expiry", "")).strip()
    if not (16 <= len(number) <= 19) or not luhn_ok(number):
        return Response({"detail": msg(request, "card_invalid")}, status=400)
    m = re.fullmatch(r"(\d{2})/?(\d{2})", expiry)
    if not m or not (1 <= int(m.group(1)) <= 12):
        return Response({"detail": msg(request, "card_expired")}, status=400)
    mm, yy = int(m.group(1)), int(m.group(2))
    now = timezone.localdate()
    if (2000 + yy, mm) < (now.year, now.month):
        return Response({"detail": msg(request, "card_expired")}, status=400)

    provider = get_provider()
    r = provider.start_binding(number, f"{mm:02d}/{yy:02d}")
    v = CardVerification.objects.create(
        user=request.user, session=secrets.token_urlsafe(24), pending_token=r["token"], masked=mask(number),
        brand=card_brand(number), expiry=f"{mm:02d}/{yy:02d}", phone_hint=r["phone_hint"],
        otp_hash=hash_otp(r["otp"]), expires_at=timezone.now() + timedelta(minutes=3))
    resp = {"session": v.session, "phone_hint": v.phone_hint, "expires_in": 180}
    if provider.returns_code:
        resp["sandbox_code"] = r["otp"]          # faqat sinov rejimida!
    return Response(resp, status=201)


@S
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def verify_card(request):
    """{session, code} — SMS kodni tasdiqlash, karta saqlanadi."""
    v = get_object_or_404(CardVerification, session=request.data.get("session", ""), user=request.user)
    if v.expires_at < timezone.now() or v.attempts >= 5:
        v.delete()
        return Response({"detail": msg(request, "otp_expired")}, status=400)
    if hash_otp(str(request.data.get("code", "")).strip()) != v.otp_hash:
        v.attempts += 1
        v.save(update_fields=["attempts"])
        return Response({"detail": msg(request, "otp_wrong")}, status=400)
    card = PaymentCard.objects.create(user=request.user, token=v.pending_token, masked=v.masked,
                                      brand=v.brand, expiry=v.expiry)
    v.delete()
    return Response(card_dict(card), status=201)


@S
@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def delete_card(request, pk):
    c = get_object_or_404(PaymentCard, pk=pk, user=request.user)
    c.is_active = False
    c.save(update_fields=["is_active"])
    return Response(status=204)


@S
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def pay_order(request, pk):
    """{card_id} — butun buyurtma (barcha dorixonalar + taksi) uchun BITTA to'lov."""
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk, user=request.user)
        if order.is_paid:
            return Response({"detail": msg(request, "already_paid")}, status=400)
        if order.status != Order.Status.AWAITING_PAYMENT:
            return Response({"detail": msg(request, "bad_status")}, status=400)
        card = PaymentCard.objects.filter(pk=request.data.get("card_id"), user=request.user, is_active=True).first()
        if not card:
            return Response({"detail": msg(request, "card_required")}, status=400)
        payment = order.payments.filter(status=Payment.Status.PENDING).first() or \
            Payment.objects.create(order=order, amount=order.total, method="card")
        r = get_provider().charge(card.token, order.total, f"Medora buyurtma #{order.id}")
        if not r["ok"]:
            payment.status = Payment.Status.FAILED
            payment.card = card
            payment.save(update_fields=["status", "card"])
            Payment.objects.create(order=order, amount=order.total, method="card")   # qayta urinish uchun
            return Response({"detail": msg(request, r["error"] or "insufficient")}, status=402)
        payment.status, payment.card, payment.provider_ref, payment.paid_at = \
            Payment.Status.PAID, card, r["ref"], timezone.now()
        payment.save()
        order.is_paid = True
        order.status = Order.Status.CONFIRMED
        order.save(update_fields=["is_paid", "status"])
    sync_order_status(order)
    return Response({"ok": True, "order_id": order.id, "amount": order.total, "card": card.masked})
