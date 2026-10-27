from rest_framework import serializers

from .models import Reservation


class ReservationSerializer(serializers.ModelSerializer):
    medicine = serializers.SerializerMethodField()
    pharmacy = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    customer = serializers.CharField(source="user.first_name", read_only=True)
    customer_phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = Reservation
        fields = ("id", "inventory", "quantity", "status", "status_label", "code",
                  "created_at", "expires_at", "hold_minutes", "medicine", "pharmacy", "customer", "customer_phone")
        read_only_fields = ("status", "code", "created_at", "expires_at")

    def get_medicine(self, obj):
        m = obj.inventory.medicine
        return {"id": m.id, "name": m.name, "dosage": m.dosage, "form": m.form}

    def get_pharmacy(self, obj):
        p = obj.inventory.pharmacy
        return {"id": p.id, "name": p.name, "address": p.address, "phone": p.phone, "lat": p.lat, "lng": p.lng}


class ReservationCreateSerializer(serializers.Serializer):
    inventory_id = serializers.IntegerField()
    lat = serializers.FloatField(required=False)
    lng = serializers.FloatField(required=False)
    quantity = serializers.IntegerField(min_value=1, max_value=10, default=1)
