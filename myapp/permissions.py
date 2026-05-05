"""myapp/permissions.py — Custom DRF permission classes."""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    message = "Access restricted to Admins only."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "Admin")


class IsDriver(BasePermission):
    message = "Access restricted to Drivers only."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "Driver")


class IsUser(BasePermission):
    message = "Access restricted to Users only."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "User")


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.role == "Admin"


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == "Admin":
            return True
        return getattr(obj, "user_id", None) == request.user.pk