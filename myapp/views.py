"""myapp/views.py — All views for Digga."""

import logging
from django.shortcuts import render
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q

from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import Person, Vehicle, DriverVehicle, Booking, Payment, Rating
from .serializers import (
    PersonSerializer, VehicleSerializer,
    BookingSerializer, PaymentSerializer,
    RatingSerializer, LoginSerializer,
    DriverVehicleSerializer, DriverVehicleCreateSerializer,
    DriverVehicleListSerializer, DriverVehicleAdminSerializer,
)
from .permissions import IsAdmin, IsDriver

logger = logging.getLogger("myapp")


# ─── Frontend views ───────────────────────────────────────────────────────────

def home(request):
    return render(request, "myapp/index.html")

def login_page(request):
    return render(request, "myapp/login.html")

def register_page(request):
    return render(request, "myapp/register.html")

def admin_dashboard(request):
    return render(request, "myapp/admin.html")

def driver_dashboard(request):
    return render(request, "myapp/driver.html")

def user_dashboard(request):
    return render(request, "myapp/user.html")

def vehicle_list(request):
    return render(request, "myapp/vehicle.html")

def booking_live(request):
    return render(request, "myapp/booking_live.html")

def driver_requests(request):
    return render(request, "myapp/request.html")

def driver_earnings(request):
    return render(request, "myapp/earning.html")

def driver_vehicle(request):
    return render(request, "myapp/driver_vehicle.html")

def driver_fleet(request):
    return render(request, "myapp/driver_fleet.html")

def my_bookings(request):
    return render(request, "myapp/my_bookings.html")

def track_ride(request, booking_id):
    return render(request, "myapp/track_ride.html", {"booking_id": booking_id})


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginView(APIView):
    permission_classes    = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            if isinstance(errors, dict) and "non_field_errors" in errors:
                inner = errors["non_field_errors"]
                if isinstance(inner, list) and inner:
                    inner = inner[0]
                if isinstance(inner, dict):
                    return Response(inner, status=status.HTTP_400_BAD_REQUEST)
                return Response({"detail": str(inner)}, status=status.HTTP_400_BAD_REQUEST)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]
        try:
            refresh     = RefreshToken.for_user(user)
            access      = str(refresh.access_token)
            refresh_str = str(refresh)
        except Exception as exc:
            logger.exception("Token generation failed for user pk=%s: %s", user.pk, exc)
            return Response(
                {"detail": f"Could not generate tokens: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "access":   access,
            "refresh":  refresh_str,
            "role":     user.role,
            "user_id":  user.person_id,
            "name":     user.name,
            "email":    user.email,
        })


# ─── Logout ───────────────────────────────────────────────────────────────────

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            pass
        return Response({"detail": "Logged out successfully."})


# ─── Me ───────────────────────────────────────────────────────────────────────

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PersonSerializer(request.user).data)

    def patch(self, request):
        ser = PersonSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


# ─── Admin Stats ──────────────────────────────────────────────────────────────

class AdminStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        total_users      = Person.objects.filter(role="User").count()
        total_drivers    = Person.objects.filter(role="Driver").count()
        total_vehicles   = Vehicle.objects.count()
        live_vehicles    = Vehicle.objects.filter(status="available").count()
        active_bookings  = Booking.objects.filter(status__in=["pending", "accepted", "ongoing"]).count()
        total_revenue    = (
            Booking.objects.filter(status="completed")
            .aggregate(rev=Sum("total_amount"))["rev"] or 0
        )
        pending_dv       = DriverVehicle.objects.filter(is_verified=False, is_deleted=False).count()
        return Response({
            "total_users":      total_users,
            "total_drivers":    total_drivers,
            "total_vehicles":   total_vehicles,
            "live_vehicles":    live_vehicles,
            "active_bookings":  active_bookings,
            "total_revenue":    float(total_revenue),
            "pending_driver_vehicles": pending_dv,
        })


# ─── Persons ──────────────────────────────────────────────────────────────────

class PersonViewSet(viewsets.ModelViewSet):
    queryset         = Person.objects.all().order_by("person_id")
    serializer_class = PersonSerializer

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs   = super().get_queryset()
        user = self.request.user
        if user.role != "Admin":
            return qs.filter(pk=user.pk)
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return qs


# ─── Vehicles ─────────────────────────────────────────────────────────────────

class VehicleViewSet(viewsets.ModelViewSet):
    queryset         = Vehicle.objects.select_related("driver").order_by("vehicle_id")
    serializer_class = VehicleSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve") and self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        if self.request.query_params.get("driver"):
            qs = qs.filter(driver_id=self.request.query_params["driver"])
        return qs

    @action(detail=True, methods=["patch"], url_path="location")
    def update_location(self, request, pk=None):
        vehicle = self.get_object()
        user    = request.user
        if user.role != "Admin" and vehicle.driver_id != user.pk:
            return Response({"detail": "Not your vehicle."}, status=403)

        lat = request.data.get("lat")
        lng = request.data.get("lng")
        if lat is None or lng is None:
            return Response({"detail": "lat and lng are required."}, status=400)

        try:
            vehicle.driver_lat = float(lat)
            vehicle.driver_lng = float(lng)
            vehicle.save(update_fields=["driver_lat", "driver_lng"])
        except (TypeError, ValueError):
            return Response({"detail": "Invalid coordinates."}, status=400)

        return Response({"driver_lat": vehicle.driver_lat, "driver_lng": vehicle.driver_lng})


# ─── DriverVehicle — Driver CRUD ──────────────────────────────────────────────

class DriverVehicleViewSet(viewsets.ModelViewSet):
    """Driver manages their own vehicles. Supports multipart (image upload)."""
    permission_classes = [IsAuthenticated]
    parser_classes     = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        user = self.request.user
        qs   = DriverVehicle.objects.filter(is_deleted=False).select_related("driver")
        if user.role == "Driver":
            qs = qs.filter(driver=user)
        elif user.role != "Admin":
            # Users can see verified available ones
            qs = qs.filter(is_verified=True, is_available=True)
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return DriverVehicleListSerializer
        return DriverVehicleSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != "Driver":
            raise PermissionError("Only drivers can add vehicles.")
        serializer.save(driver=user)

    def perform_update(self, serializer):
        instance = serializer.save()
        # If already linked to a Vehicle, sync price and availability
        if instance.linked_vehicle:
            lv = instance.linked_vehicle
            lv.price_per_km = instance.price_per_km
            lv.capacity     = instance.capacity
            if not instance.is_available:
                lv.status = "inactive"
            elif lv.status == "inactive":
                lv.status = "available"
            lv.save(update_fields=["price_per_km", "capacity", "status"])

    def perform_destroy(self, instance):
        """Soft delete — keep DB record for audit."""
        instance.is_deleted = True
        instance.is_available = False
        instance.save(update_fields=["is_deleted", "is_available"])
        if instance.linked_vehicle:
            instance.linked_vehicle.status = "inactive"
            instance.linked_vehicle.save(update_fields=["status"])

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.driver != request.user and request.user.role != "Admin":
            return Response({"detail": "Not your vehicle."}, status=403)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── DriverVehicle — Admin Management ────────────────────────────────────────

class AdminDriverVehicleViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin views all driver-submitted vehicles and can verify/reject them."""
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class   = DriverVehicleAdminSerializer

    def get_queryset(self):
        qs       = DriverVehicle.objects.select_related("driver", "linked_vehicle").order_by("-created_at")
        category = self.request.query_params.get("category")
        verified = self.request.query_params.get("is_verified")
        deleted  = self.request.query_params.get("include_deleted", "false")

        if deleted.lower() != "true":
            qs = qs.filter(is_deleted=False)
        if category:
            qs = qs.filter(category=category)
        if verified is not None:
            qs = qs.filter(is_verified=(verified.lower() == "true"))
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    @action(detail=True, methods=["patch"], url_path="verify")
    def verify(self, request, pk=None):
        """
        PATCH /api/admin/driver-vehicles/{id}/verify/
        Body: {"action": "approve"} or {"action": "reject"}
        """
        dv     = self.get_object()
        act    = request.data.get("action", "approve")

        if act == "approve":
            with transaction.atomic():
                dv.is_verified = True
                if not dv.linked_vehicle:
                    # Auto-create a Vehicle entry so bookings work
                    vehicle = Vehicle.objects.create(
                        driver       = dv.driver,
                        vehicle_type = f"{dv.brand} {dv.model_name}",
                        capacity     = dv.capacity,
                        price_per_km = dv.price_per_km,
                        status       = "available" if dv.is_available else "inactive",
                    )
                    dv.linked_vehicle = vehicle
                else:
                    dv.linked_vehicle.status = "available" if dv.is_available else "inactive"
                    dv.linked_vehicle.save(update_fields=["status"])
                dv.save()
            return Response(
                DriverVehicleAdminSerializer(dv, context={"request": request}).data
            )

        elif act == "reject":
            with transaction.atomic():
                dv.is_verified = False
                if dv.linked_vehicle:
                    dv.linked_vehicle.status = "inactive"
                    dv.linked_vehicle.save(update_fields=["status"])
                dv.save(update_fields=["is_verified"])
            return Response(
                DriverVehicleAdminSerializer(dv, context={"request": request}).data
            )

        return Response({"detail": "action must be 'approve' or 'reject'."}, status=400)

    @action(detail=True, methods=["patch"], url_path="disable")
    def disable(self, request, pk=None):
        """Admin disables a driver vehicle immediately."""
        dv = self.get_object()
        with transaction.atomic():
            dv.is_available = False
            dv.save(update_fields=["is_available"])
            if dv.linked_vehicle:
                dv.linked_vehicle.status = "inactive"
                dv.linked_vehicle.save(update_fields=["status"])
        return Response({"detail": "Vehicle disabled.", "id": dv.pk})


# ─── Bookings ─────────────────────────────────────────────────────────────────

class BookingViewSet(viewsets.ModelViewSet):
    queryset         = Booking.objects.select_related("user", "vehicle").order_by("-booking_time")
    serializer_class = BookingSerializer

    def get_queryset(self):
        user = self.request.user
        qs   = super().get_queryset()

        if user.role == "User":
            qs = qs.filter(user=user)
        elif user.role == "Driver":
            vehicle_ids = Vehicle.objects.filter(driver=user).values_list("vehicle_id", flat=True)
            qs          = qs.filter(vehicle_id__in=vehicle_ids)

        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        booking = self.get_object()
        if booking.status != "pending":
            return Response({"detail": f"Cannot accept a '{booking.status}' booking."}, status=400)
        user = request.user
        if user.role == "Driver" and (
            not booking.vehicle or booking.vehicle.driver_id != user.pk
        ):
            return Response({"detail": "This booking is not for your vehicle."}, status=403)

        with transaction.atomic():
            booking.status     = "accepted"
            booking.start_time = timezone.now()
            booking.save()
            if booking.vehicle:
                booking.vehicle.status = "busy"
                booking.vehicle.save()
        return Response({"status": "accepted", "booking_id": booking.booking_id})

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        booking = self.get_object()
        if booking.status != "accepted":
            return Response({"detail": "Booking must be accepted before starting."}, status=400)
        booking.status = "ongoing"
        booking.save()
        return Response({"status": "ongoing"})

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        booking = self.get_object()
        if booking.status not in ("accepted", "ongoing"):
            return Response({"detail": f"Cannot complete a '{booking.status}' booking."}, status=400)
        with transaction.atomic():
            booking.status   = "completed"
            booking.end_time = timezone.now()
            booking.save()
            if booking.vehicle:
                booking.vehicle.status = "available"
                booking.vehicle.save()
        return Response({"status": "completed"})

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status in ("completed", "cancelled"):
            return Response({"detail": f"Cannot cancel a '{booking.status}' booking."}, status=400)
        with transaction.atomic():
            booking.status = "cancelled"
            booking.save()
            if booking.vehicle:
                booking.vehicle.status = "available"
                booking.vehicle.save()
        return Response({"status": "cancelled"})


# ─── Payments ─────────────────────────────────────────────────────────────────

class PaymentViewSet(viewsets.ModelViewSet):
    queryset         = Payment.objects.select_related("booking").order_by("-payment_date")
    serializer_class = PaymentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == "User":
            qs = qs.filter(booking__user=self.request.user)
        elif self.request.user.role == "Driver":
            ids = Vehicle.objects.filter(driver=self.request.user).values_list("vehicle_id", flat=True)
            qs  = qs.filter(booking__vehicle_id__in=ids)
        return qs


# ─── Ratings ──────────────────────────────────────────────────────────────────

class RatingViewSet(viewsets.ModelViewSet):
    queryset         = Rating.objects.select_related("user", "driver", "booking").order_by("-rating_time")
    serializer_class = RatingSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == "User":
            qs = qs.filter(user=self.request.user)
        elif self.request.user.role == "Driver":
            qs = qs.filter(driver=self.request.user)
        return qs