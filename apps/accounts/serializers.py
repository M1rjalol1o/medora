from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    pharmacy_name = serializers.CharField(source="pharmacy.name", default=None, read_only=True)
    taxi_park_name = serializers.CharField(source="taxi_park.name", default=None, read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "phone", "role", "language", "pharmacy", "pharmacy_name",
                  "taxi_park", "taxi_park_name")
        read_only_fields = ("role", "pharmacy", "taxi_park")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("username", "password", "first_name", "phone")

    def create(self, data):
        return User.objects.create_user(role=User.Role.CUSTOMER, **data)
