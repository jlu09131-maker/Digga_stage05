"""myapp/admin.py — Django Admin configuration for Digga models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Person, Vehicle, Booking, Payment, Rating


@admin.register(Person)
class PersonAdmin(BaseUserAdmin):
    list_display = ("person_id", "name", "email", "mobile", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("name", "email", "mobile")
    ordering = ("person_id",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("name", "mobile")}),
        ("Permissions", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "name", "mobile", "role", "password1", "password2")}),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("vehicle_id", "vehicle_type", "driver", "capacity", "price_per_km", "status", "created_at")
    list_filter = ("status", "vehicle_type")
    search_fields = ("vehicle_type", "driver__name")
    ordering = ("vehicle_id",)
    readonly_fields = ("created_at",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("booking_id", "user", "vehicle", "pickup_location", "drop_location", "status", "total_amount", "booking_time")
    list_filter = ("status",)
    search_fields = ("user__name", "user__email", "pickup_location")
    ordering = ("-booking_time",)
    readonly_fields = ("booking_time", "distance_km", "total_amount")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "booking", "amount", "payment_mode", "payment_status", "payment_date")
    list_filter = ("payment_status", "payment_mode")
    ordering = ("-payment_date",)
    readonly_fields = ("payment_date",)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("rating_id", "user", "driver", "booking", "rating_value", "rating_time")
    list_filter = ("rating_value",)
    ordering = ("-rating_time",)
    readonly_fields = ("rating_time",)