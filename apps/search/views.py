from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.catalog.models import Medicine
from apps.catalog.utils import normalize
from apps.pharmacies.models import Inventory
from apps.reservations.models import Reservation, hold_minutes_for

from .geo import haversine_km, travel_minutes
from .prediction import availability_probability, hourly_rates
from .ranking import rank_offers

# Lokatsiya berilmasa — Toshkent markazi (Amir Temur xiyoboni)
DEFAULT_LAT, DEFAULT_LNG = 41.3111, 69.2797


def _medicine_dict(m: Medicine) -> dict:
    return {
        "id": m.id, "name": m.name, "inn": m.inn, "form": m.form, "dosage": m.dosage,
        "manufacturer": m.manufacturer, "requires_prescription": m.requires_prescription,
    }


@extend_schema(parameters=[OpenApiParameter("q", str)], responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
def medicine_search(request):
    """Dori nomi bo'yicha qidiruv (autocomplete). ?q=paratsetamol"""
    q = normalize(request.GET.get("q", ""))
    if len(q) < 2:
        return Response([])
    cond = Q()
    for word in q.split():
        cond &= Q(search_text__contains=word)
    meds = Medicine.objects.filter(cond)[:20]
    return Response([_medicine_dict(m) for m in meds])


@extend_schema(parameters=[OpenApiParameter("lat", float), OpenApiParameter("lng", float),
                           OpenApiParameter("mode", str, enum=["normal", "urgent"]),
                           OpenApiParameter("travel", str, enum=["car", "walk"])], responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
def medicine_offers(request, medicine_id: int):
    """
    Dori qaysi dorixonalarda bor, nechta, yetib borguncha qolish ehtimoli.
    ?lat=&lng=&mode=normal|urgent&travel=car|walk
    """
    medicine = get_object_or_404(Medicine, pk=medicine_id)
    try:
        lat = float(request.GET.get("lat", DEFAULT_LAT))
        lng = float(request.GET.get("lng", DEFAULT_LNG))
    except ValueError:
        lat, lng = DEFAULT_LAT, DEFAULT_LNG
    mode = request.GET.get("mode", "normal")
    travel = request.GET.get("travel", "car")

    Reservation.objects.expire_overdue()
    items = list(
        Inventory.objects.select_related("pharmacy")
        .filter(medicine=medicine, pharmacy__is_active=True)
    )
    rates = hourly_rates(medicine.id, [i.pharmacy_id for i in items])

    offers = []
    for inv in items:
        ph = inv.pharmacy
        dist = haversine_km(lat, lng, ph.lat, ph.lng)
        eta = travel_minutes(dist, travel)
        available = inv.available_quantity
        rate = rates.get(ph.id, 0)
        prob = availability_probability(available, rate, eta) if ph.is_open_now() else 0.0
        offers.append({
            "inventory_id": inv.id,
            "pharmacy": {
                "id": ph.id, "name": ph.name, "address": ph.address, "phone": ph.phone,
                "lat": ph.lat, "lng": ph.lng, "is_open": ph.is_open_now(), "is_24h": ph.is_24h,
            },
            "available": available,
            "price": inv.final_price,
            "old_price": int(inv.price) if inv.discount_percent else None,
            "discount_percent": inv.discount_percent,
            "expiry_date": inv.expiry_date,
            "requires_prescription": medicine.requires_prescription,
            "distance_km": round(dist, 2),
            "eta_minutes": round(eta, 1),
            "sales_per_hour": round(rate, 2),
            "hold_minutes": hold_minutes_for(ph, lat, lng),
            "probability": round(prob, 3),
            "updated_at": inv.updated_at,
        })

    ranked = rank_offers(offers, mode, travel)
    return Response({"medicine": _medicine_dict(medicine), "mode": mode, "travel": travel, "offers": ranked})


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(["POST"])
def basket_search(request):
    """
    Bir nechta dorini birga qidirish (retsept).
    body: {items:[{medicine_id, quantity}], lat, lng, mode: normal|urgent, travel: car|walk}
    """
    from .basket import plan_basket
    d = request.data
    try:
        lat = float(d.get("lat", DEFAULT_LAT))
        lng = float(d.get("lng", DEFAULT_LNG))
    except (TypeError, ValueError):
        lat, lng = DEFAULT_LAT, DEFAULT_LNG
    wanted, seen = [], set()
    for it in d.get("items", [])[:8]:
        try:
            mid, qty = int(it.get("medicine_id")), max(1, min(int(it.get("quantity") or 1), 20))
        except (TypeError, ValueError):
            continue
        m = Medicine.objects.filter(pk=mid).first()
        if m and mid not in seen:
            seen.add(mid)
            wanted.append((m, qty))
    if not wanted:
        return Response({"detail": "items"}, status=400)
    Reservation.objects.expire_overdue()
    return Response(plan_basket(wanted, lat, lng, d.get("mode", "normal"), d.get("travel", "car")))
