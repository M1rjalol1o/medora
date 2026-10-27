from rest_framework import serializers

from .models import Order, PharmacyOrder


class OrderItemSerializer(serializers.Serializer):
    medicine_name = serializers.CharField()
    quantity = serializers.IntegerField()
    price = serializers.IntegerField()
    requires_prescription = serializers.BooleanField()


class StopSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sequence = serializers.IntegerField()
    kind = serializers.CharField()
    title = serializers.CharField()
    address = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    done_at = serializers.DateTimeField()
    pharmacy_order_id = serializers.IntegerField(allow_null=True)


def driver_dict(d):
    if not d:
        return None
    return {"id": d.id, "name": d.user.first_name, "phone": d.user.phone, "car_model": d.car_model,
            "car_number": d.car_number, "lat": d.lat, "lng": d.lng, "rating": float(d.rating),
            "park": d.park.name}


def delivery_dict(d, with_codes=False):
    if not d:
        return None
    return {
        "id": d.id, "status": d.status, "fee": d.fee, "distance_km": d.distance_km,
        "driver": driver_dict(d.driver), "cash_collected": d.cash_collected,
        "stops": StopSerializer(d.stops.all(), many=True).data,
        "driver_earning": d.driver_earning, "park_earning": d.park_earning,
    }


class PharmacyOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    pharmacy = serializers.SerializerMethodField()

    class Meta:
        model = PharmacyOrder
        fields = ("id", "status", "subtotal", "pickup_code", "pharmacy", "items", "rx_verified", "updated_at")

    def get_pharmacy(self, o):
        p = o.pharmacy
        return {"id": p.id, "name": p.name, "address": p.address, "phone": p.phone, "lat": p.lat, "lng": p.lng}


class OrderSerializer(serializers.ModelSerializer):
    pharmacy_orders = PharmacyOrderSerializer(many=True)
    delivery = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("id", "status", "fulfillment", "payment_method", "is_paid", "payment_status", "address", "lat",
                  "lng", "comment", "items_total", "delivery_fee", "total", "delivery_code", "created_at",
                  "pharmacy_orders", "delivery", "prescription", "customer")

    def get_delivery(self, o):
        return delivery_dict(getattr(o, "delivery", None))

    def get_payment_status(self, o):
        p = o.payments.order_by("-created_at").first()
        return p.status if p else None

    def get_customer(self, o):
        return {"name": o.user.first_name or o.user.username, "phone": o.user.phone}
