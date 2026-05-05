"""myapp/models.py — All database models for Digga."""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class PersonManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "Admin")
        return self.create_user(email, password, **extra_fields)


class Person(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("Admin", "Admin"),
        ("Driver", "Driver"),
        ("User", "User"),
    ]

    person_id  = models.AutoField(primary_key=True)
    name       = models.CharField(max_length=100)
    email      = models.EmailField(unique=True)
    mobile     = models.CharField(max_length=15, unique=True)
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES, default="User")
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["name", "mobile"]

    objects = PersonManager()

    class Meta:
        db_table = "person"

    def __str__(self):
        return f"{self.name} ({self.role})"

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name.split()[0]


class Vehicle(models.Model):
    STATUS_CHOICES = [
        ("available", "Available"),
        ("busy",      "Busy"),
        ("inactive",  "Inactive"),
    ]

    vehicle_id       = models.AutoField(primary_key=True)
    driver           = models.ForeignKey(
        Person, on_delete=models.SET_NULL,
        null=True, blank=True, db_column="driver_id",
        related_name="vehicles",
    )
    vehicle_type     = models.CharField(max_length=50)
    capacity         = models.IntegerField(null=True, blank=True)
    price_per_km     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")
    current_location = models.CharField(max_length=200, null=True, blank=True)
    driver_lat       = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    driver_lng       = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vehicle"

    def __str__(self):
        return f"{self.vehicle_type} [#{self.vehicle_id}] — {self.status}"


class DriverVehicle(models.Model):
    """Self-managed vehicles uploaded by drivers; verified by admin."""

    CATEGORY_CHOICES = [
        ("micro_truck",  "Micro Truck"),
        ("mini_truck",   "Mini Truck"),
        ("pickup_truck", "Pickup Truck"),
        ("light_truck",  "Light Truck"),
        ("medium_truck", "Medium Truck"),
        ("heavy_truck",  "Heavy Truck"),
        ("trailer",      "Trailer"),
        ("flatbed",      "Flatbed"),
        ("dumper",       "Dumper"),
        ("jcb",          "JCB"),
        ("excavator",    "Excavator"),
        ("tractor",      "Tractor"),
    ]

    driver        = models.ForeignKey(
        Person, on_delete=models.CASCADE,
        related_name="driver_vehicles",
        limit_choices_to={"role": "Driver"},
        db_column="driver_id",
    )
    category      = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    subtype       = models.CharField(max_length=100)
    brand         = models.CharField(max_length=100)
    model_name    = models.CharField(max_length=100)
    image         = models.ImageField(upload_to="driver_vehicles/", null=True, blank=True)
    number_plate  = models.CharField(max_length=20, unique=True)
    capacity      = models.PositiveIntegerField()
    price_per_km  = models.DecimalField(max_digits=10, decimal_places=2)
    description   = models.TextField(null=True, blank=True)
    is_available  = models.BooleanField(default=True)
    is_verified   = models.BooleanField(default=False)
    is_deleted    = models.BooleanField(default=False)          # soft delete
    linked_vehicle = models.OneToOneField(
        Vehicle, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="driver_vehicle_source",
    )
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "driver_vehicle"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.brand} {self.model_name} [{self.number_plate}] — {'✓' if self.is_verified else '⏳'}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending",   "Pending"),
        ("accepted",  "Accepted"),
        ("ongoing",   "Ongoing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    booking_id      = models.AutoField(primary_key=True)
    user            = models.ForeignKey(
        Person, on_delete=models.CASCADE,
        db_column="user_id", related_name="bookings",
    )
    vehicle         = models.ForeignKey(
        Vehicle, on_delete=models.SET_NULL,
        null=True, blank=True, db_column="vehicle_id", related_name="bookings",
    )
    pickup_location = models.CharField(max_length=200)
    drop_location   = models.CharField(max_length=200)
    pickup_lat      = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    pickup_lng      = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    drop_lat        = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    drop_lng        = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    distance_km     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_amount    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    booking_time    = models.DateTimeField(auto_now_add=True)
    start_time      = models.DateTimeField(null=True, blank=True)
    end_time        = models.DateTimeField(null=True, blank=True)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    class Meta:
        db_table = "booking"
        ordering = ["-booking_time"]

    def __str__(self):
        return f"Booking #{self.booking_id} by {self.user.name} — {self.status}"


class Payment(models.Model):
    MODE_CHOICES = [
        ("cash", "Cash"),
        ("upi",  "UPI"),
        ("card", "Card"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed",  "Failed"),
    ]

    payment_id       = models.AutoField(primary_key=True)
    booking          = models.OneToOneField(Booking, on_delete=models.CASCADE, db_column="booking_id")
    amount           = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode     = models.CharField(max_length=10, choices=MODE_CHOICES)
    payment_status   = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    transaction_id   = models.CharField(max_length=100, null=True, blank=True)
    gateway_response = models.TextField(null=True, blank=True)
    payment_date     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payment"

    def __str__(self):
        return f"Payment #{self.payment_id} ₹{self.amount} — {self.payment_status}"


class Rating(models.Model):
    rating_id    = models.AutoField(primary_key=True)
    user         = models.ForeignKey(
        Person, on_delete=models.CASCADE,
        db_column="user_id", related_name="given_ratings",
    )
    driver       = models.ForeignKey(
        Person, on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="driver_id", related_name="received_ratings",
    )
    booking      = models.ForeignKey(Booking, on_delete=models.CASCADE, db_column="booking_id")
    rating_value = models.PositiveSmallIntegerField()
    review       = models.TextField(null=True, blank=True)
    rating_time  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rating"
        unique_together = ("user", "booking")

    def __str__(self):
        return f"Rating {self.rating_value}★ — Booking #{self.booking_id}"