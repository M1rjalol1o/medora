from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.i18n import msg
from apps.prescriptions.models import Prescription

from . import services
from .models import Order
from .serializers import OrderSerializer

S = extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)


def order_qs():
    return Order.objects.select_related("user", "delivery__driver__user", "delivery__driver__park").prefetch_related(
        "pharmacy_orders__items", "pharmacy_orders__pharmacy", "delivery__stops", "payments")


@S
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def quote(request):
    """Savat: mahsulotlar + yetkazish narxi. body: {items:[{inventory_id,quantity}], fulfillment, lat, lng}"""
    d = request.data
    return Response(services.quote(d.get("items", []), d.get("fulfillment", "delivery"), d.get("lat"), d.get("lng")))


@S
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def orders(request):
    services.expire_unpaid()
    if request.method == "GET":
        return Response(OrderSerializer(order_qs().filter(user=request.user)[:30], many=True).data)

    d = request.data
    fulfillment = d.get("fulfillment", "delivery")
    method = d.get("payment_method", "card")
    if fulfillment not in ("delivery", "pickup") or method not in ("card", "cash"):
        return Response({"detail": msg(request, "bad_value", f="fulfillment/payment_method")}, status=400)
    if fulfillment == "delivery" and (d.get("lat") is None or d.get("lng") is None):
        return Response({"detail": msg(request, "bad_value", f="lat/lng")}, status=400)
    rx = None
    if d.get("prescription_id"):
        rx = get_object_or_404(Prescription, pk=d["prescription_id"], user=request.user)
    try:
        order = services.create_order(
            request.user, d.get("items", []), fulfillment, method, address=d.get("address", ""),
            lat=d.get("lat"), lng=d.get("lng"), prescription=rx, comment=d.get("comment", ""))
    except services.OrderError as e:
        return Response({"detail": msg(request, e.key, **e.kw)}, status=status.HTTP_409_CONFLICT)
    return Response(OrderSerializer(order_qs().get(pk=order.pk)).data, status=201)


@S
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def order_detail(request, pk):
    services.expire_unpaid()
    o = get_object_or_404(order_qs(), pk=pk, user=request.user)
    return Response(OrderSerializer(o).data)


@S
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def order_cancel(request, pk):
    o = get_object_or_404(Order, pk=pk, user=request.user)
    d = getattr(o, "delivery", None)
    if o.status in ("completed", "cancelled", "delivering") or (d and d.status not in ("searching", "assigned")):
        return Response({"detail": msg(request, "cannot_cancel")}, status=400)
    if o.pharmacy_orders.filter(status__in=["picked_up", "issued"]).exists():
        return Response({"detail": msg(request, "cannot_cancel")}, status=400)
    services.cancel_order(o)
    return Response(OrderSerializer(order_qs().get(pk=pk)).data)
