"""myapp/serializers.py — DRF serializers with full validation."""

import logging
from math import radians, sin, cos, sqrt, atan2
from rest_framework import serializers
from .models import Person, Vehicle, DriverVehicle, Booking, Payment, Rating

logger = logging.getLogger("myapp")


# ─── Helper ───────────────────────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    """Return great-circle distance in kilometres."""
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return round(2 * atan2(sqrt(a), sqrt(1 - a)) * 6371, 2)


# ─── Person ───────────────────────────────────────────────────────────────────

class PersonSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model  = Person
        fields = [
            "person_id", "name", "email", "mobile", "password",
            "role", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["person_id", "created_at", "updated_at"]

    def validate_email(self, value):
        value = value.lower().strip()
        qs = Person.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_mobile(self, value):
        value   = value.strip()
        cleaned = value.replace(" ", "").replace("-", "")
        if not cleaned.lstrip("+").isdigit():
            raise serializers.ValidationError("Enter a valid mobile number.")
        qs = Person.objects.filter(mobile=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This mobile number is already registered.")
        return value

    def validate_role(self, value):
        allowed = {"Admin", "Driver", "User"}
        if value not in allowed:
            raise serializers.ValidationError(f"Role must be one of: {', '.join(allowed)}.")
        return value

    def validate(self, data):
        if not self.instance and not data.get("password"):
            raise serializers.ValidationError({"password": "Password is required."})
        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Person.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class PersonMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Person
        fields = ["person_id", "name", "email", "role"]


# ─── Vehicle ──────────────────────────────────────────────────────────────────

class VehicleSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source="driver.name", read_only=True, default=None)
    # Extra fields populated from linked DriverVehicle (when available)
    category    = serializers.SerializerMethodField()
    subtype     = serializers.SerializerMethodField()
    image_url   = serializers.SerializerMethodField()

    class Meta:
        model  = Vehicle
        fields = [
            "vehicle_id", "driver", "driver_name", "vehicle_type",
            "capacity", "price_per_km", "status", "current_location",
            "driver_lat", "driver_lng",
            "category", "subtype", "image_url",
            "created_at",
        ]
        read_only_fields = ["vehicle_id", "created_at"]

    def _get_driver_vehicle(self, obj):
        try:
            return obj.driver_vehicle_source
        except Exception:
            return None

    def get_category(self, obj):
        dv = self._get_driver_vehicle(obj)
        return dv.get_category_display() if dv else None

    def get_subtype(self, obj):
        dv = self._get_driver_vehicle(obj)
        return dv.subtype if dv else None

    def get_image_url(self, obj):
        dv = self._get_driver_vehicle(obj)
        if dv and dv.image:
            request = self.context.get("request")
            return request.build_absolute_uri(dv.image.url) if request else dv.image.url
        return None

    def validate_price_per_km(self, value):
        if value < 0:
            raise serializers.ValidationError("Price per km cannot be negative.")
        return value

    def validate_status(self, value):
        allowed = {"available", "busy", "inactive"}
        if value not in allowed:
            raise serializers.ValidationError(f"Status must be one of: {', '.join(allowed)}.")
        return value


class VehicleMinimalSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source="driver.name", read_only=True, default=None)
    image_url   = serializers.SerializerMethodField()
    category    = serializers.SerializerMethodField()
    subtype     = serializers.SerializerMethodField()

    class Meta:
        model  = Vehicle
        fields = [
            "vehicle_id", "vehicle_type", "price_per_km", "status",
            "driver_lat", "driver_lng", "driver_name",
            "image_url", "category", "subtype",
        ]

    def _dv(self, obj):
        try:
            return obj.driver_vehicle_source
        except Exception:
            return None

    def get_image_url(self, obj):
        dv = self._dv(obj)
        if dv and dv.image:
            request = self.context.get("request")
            return request.build_absolute_uri(dv.image.url) if request else dv.image.url
        return None

    def get_category(self, obj):
        dv = self._dv(obj)
        return dv.get_category_display() if dv else None

    def get_subtype(self, obj):
        dv = self._dv(obj)
        return dv.subtype if dv else None


# ─── DriverVehicle ────────────────────────────────────────────────────────────

class DriverVehicleSerializer(serializers.ModelSerializer):
    """Full serializer used by driver for read and update."""
    driver_name        = serializers.CharField(source="driver.name", read_only=True)
    category_display   = serializers.CharField(source="get_category_display", read_only=True)
    image_url          = serializers.SerializerMethodField()

    class Meta:
        model  = DriverVehicle
        fields = [
            "id", "driver", "driver_name",
            "category", "category_display", "subtype",
            "brand", "model_name", "image", "image_url",
            "number_plate", "capacity", "price_per_km",
            "description", "is_available", "is_verified",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "driver", "is_verified", "created_at", "updated_at"]
        extra_kwargs     = {"image": {"required": False, "allow_null": True}}

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def validate_number_plate(self, value):
        value = value.strip().upper()
        qs    = DriverVehicle.objects.filter(number_plate=value, is_deleted=False)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A vehicle with this number plate already exists.")
        return value

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be a positive integer.")
        return value

    def validate_price_per_km(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price per km must be greater than zero.")
        return value


class DriverVehicleCreateSerializer(DriverVehicleSerializer):
    """Used only when a driver creates a new vehicle (driver injected from request.user)."""
    class Meta(DriverVehicleSerializer.Meta):
        read_only_fields = ["id", "driver", "is_verified", "created_at", "updated_at"]


class DriverVehicleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    driver_name      = serializers.CharField(source="driver.name", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    image_url        = serializers.SerializerMethodField()

    class Meta:
        model  = DriverVehicle
        fields = [
            "id", "driver_name", "category", "category_display",
            "subtype", "brand", "model_name", "image_url",
            "number_plate", "capacity", "price_per_km",
            "is_available", "is_verified", "created_at",
        ]

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class DriverVehicleAdminSerializer(serializers.ModelSerializer):
    """Admin-facing serializer — read-only overview + verification flag."""
    driver_name      = serializers.CharField(source="driver.name", read_only=True)
    driver_email     = serializers.CharField(source="driver.email", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    image_url        = serializers.SerializerMethodField()

    class Meta:
        model  = DriverVehicle
        fields = [
            "id", "driver", "driver_name", "driver_email",
            "category", "category_display", "subtype",
            "brand", "model_name", "image_url",
            "number_plate", "capacity", "price_per_km",
            "description", "is_available", "is_verified", "is_deleted",
            "linked_vehicle", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "driver", "driver_name", "driver_email", "category_display",
            "image_url", "created_at", "updated_at",
        ]

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


# ─── Booking ──────────────────────────────────────────────────────────────────

class BookingSerializer(serializers.ModelSerializer):
    vehicle_detail = VehicleMinimalSerializer(source="vehicle", read_only=True)
    user_name      = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model  = Booking
        fields = [
            "booking_id", "user", "user_name", "vehicle", "vehicle_detail",
            "pickup_location", "drop_location",
            "pickup_lat", "pickup_lng", "drop_lat", "drop_lng",
            "distance_km", "total_amount",
            "booking_time", "start_time", "end_time", "status",
        ]
        read_only_fields = [
            "booking_id", "user", "user_name", "vehicle_detail",
            "distance_km", "total_amount", "booking_time",
        ]

    def validate_vehicle(self, vehicle):
        if vehicle and vehicle.status != "available":
            raise serializers.ValidationError(
                f"Vehicle #{vehicle.vehicle_id} is not available (status: {vehicle.status})."
            )
        return vehicle

    def create(self, validated_data):
        p_lat = validated_data.get("pickup_lat")
        p_lng = validated_data.get("pickup_lng")
        d_lat = validated_data.get("drop_lat")
        d_lng = validated_data.get("drop_lng")

        if all(v is not None for v in [p_lat, p_lng, d_lat, d_lng]):
            distance = haversine(p_lat, p_lng, d_lat, d_lng)
        else:
            distance = 0

        vehicle      = validated_data.get("vehicle")
        price_per_km = float(vehicle.price_per_km) if vehicle else 10.0

        validated_data["distance_km"] = distance
        validated_data["total_amount"] = round(distance * price_per_km, 2)
        return super().create(validated_data)


# ─── Payment ──────────────────────────────────────────────────────────────────

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model        = Payment
        fields       = "__all__"
        read_only_fields = ["payment_id", "amount", "payment_date"]

    def validate(self, data):
        booking = data.get("booking")
        if booking and booking.status != "completed":
            raise serializers.ValidationError(
                {"booking": "Payment can only be submitted for completed rides."}
            )
        if booking and Payment.objects.filter(booking=booking).exists():
            raise serializers.ValidationError(
                {"booking": "A payment for this booking already exists."}
            )
        return data

    def create(self, validated_data):
        booking = validated_data["booking"]
        validated_data["amount"] = booking.total_amount or 0
        return super().create(validated_data)


# ─── Rating ───────────────────────────────────────────────────────────────────

class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model        = Rating
        fields       = "__all__"
        read_only_fields = ["rating_id", "rating_time"]

    def validate_rating_value(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating value must be between 1 and 5.")
        return value

    def validate(self, data):
        booking = data.get("booking")
        user    = data.get("user")
        if booking and booking.status != "completed":
            raise serializers.ValidationError({"booking": "You can only rate completed rides."})
        if booking and user and Rating.objects.filter(user=user, booking=booking).exists():
            raise serializers.ValidationError({"booking": "You have already rated this booking."})
        return data


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email    = data.get("email", "").lower().strip()
        password = data.get("password", "")

        try:
            user = Person.objects.get(email=email)
        except Person.DoesNotExist:
            raise serializers.ValidationError(
                {"detail": "No account found with this email address."}
            )

        if not user.check_password(password):
            raise serializers.ValidationError({"detail": "Incorrect password."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "Account deactivated. Contact support."})

        data["user"] = user
        return data