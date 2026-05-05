from django.urls import path
from .views import (
    home, login_page, register_page,
    admin_dashboard, driver_dashboard,
    user_dashboard, vehicle_list, booking_live,
    driver_requests, driver_earnings, driver_vehicle, driver_fleet,
    my_bookings, track_ride,
)

urlpatterns = [
    path("",                              home,             name="home"),
    path("login-page/",                   login_page,       name="login_page"),
    path("register/",                     register_page,    name="register_page"),
    path("admin-dash/",                   admin_dashboard,  name="admin_dashboard"),
    path("driver/",                       driver_dashboard, name="driver_dashboard"),
    path("user/",                         user_dashboard,   name="user_dashboard"),
    path("vehicles/",                     vehicle_list,     name="vehicle_list"),
    path("booking-live/",                 booking_live,     name="booking_live"),
    # Driver pages
    path("request/",                      driver_requests,  name="driver_requests"),
    path("earning/",                      driver_earnings,  name="driver_earnings"),
    path("driver/vehicle/",               driver_vehicle,   name="driver_vehicle"),
    path("driver/fleet/",                 driver_fleet,     name="driver_fleet"),
    # User pages
    path("my-bookings/",                  my_bookings,      name="my_bookings"),
    path("track-ride/<int:booking_id>/",  track_ride,       name="track_ride"),
]