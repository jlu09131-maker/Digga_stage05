"""myapp/api_urls.py — REST API URL configuration."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView, LogoutView, MeView, AdminStatsView,
    PersonViewSet, VehicleViewSet,
    BookingViewSet, PaymentViewSet, RatingViewSet,
    DriverVehicleViewSet, AdminDriverVehicleViewSet,
)

router = DefaultRouter()
router.register(r"persons",               PersonViewSet,              basename="person")
router.register(r"vehicles",              VehicleViewSet,             basename="vehicle")
router.register(r"bookings",              BookingViewSet,             basename="booking")
router.register(r"payments",              PaymentViewSet,             basename="payment")
router.register(r"ratings",              RatingViewSet,              basename="rating")
router.register(r"driver/vehicles",       DriverVehicleViewSet,       basename="driver-vehicle")
router.register(r"admin/driver-vehicles", AdminDriverVehicleViewSet,  basename="admin-driver-vehicle")

urlpatterns = [
    path("login/",         LoginView.as_view(),        name="api_login"),
    path("logout/",        LogoutView.as_view(),        name="api_logout"),
    path("me/",            MeView.as_view(),            name="api_me"),
    path("token/refresh/", TokenRefreshView.as_view(),  name="token_refresh"),
    path("stats/",         AdminStatsView.as_view(),    name="api_stats"),
    path("", include(router.urls)),
]