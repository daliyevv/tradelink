"""
Custom DRF permission classes for TradeLink API.

Provides role-based access control and object-level permissions.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsManufacturer(BasePermission):
    """
    Allow access only to users with role='manufacturer'.
    Used for product management endpoints.
    """

    message = 'Faqat ishlab chiqaruvchilar bu amalani amalga oshirishi mumkin.'

    def has_permission(self, request, view):
        """Check if user is a manufacturer."""
        return (
            bool(request.user and request.user.is_authenticated) and
            request.user.role == 'manufacturer'
        )


class IsDealer(BasePermission):
    """
    Allow access only to users with role='dealer'.
    Used for dealer-specific endpoints (orders, delivery, etc).
    """

    message = 'Faqat dillerlar bu amalani amalga oshirishi mumkin.'

    def has_permission(self, request, view):
        """Check if user is a dealer."""
        return (
            bool(request.user and request.user.is_authenticated) and
            request.user.role == 'dealer'
        )


class IsStoreOwner(BasePermission):
    """
    Allow access only to users with role='store'.
    Used for shopping and order endpoints.
    """

    message = 'Faqat do\'kon egalari bu amalani amalga oshirishi mumkin.'

    def has_permission(self, request, view):
        """Check if user is a store owner."""
        return (
            bool(request.user and request.user.is_authenticated) and
            request.user.role == 'store'
        )


class IsManufacturerOrDealer(BasePermission):
    """
    Allow access to users with role='manufacturer' or role='dealer'.
    Used for inventory and order processing endpoints.
    """

    message = 'Faqat ishlab chiqaruvchilar va dillerlar bu amalani amalga oshirishi mumkin.'

    def has_permission(self, request, view):
        """Check if user is a manufacturer or dealer."""
        return (
            bool(request.user and request.user.is_authenticated) and
            request.user.role in ['manufacturer', 'dealer']
        )


class IsOwnerOrReadOnly(BasePermission):
    """
    Allow object-level write access only to the owner of the object.
    Read access allowed to anyone.
    Used for user profiles, product ownership, etc.
    """

    message = 'Bu ob\'ektni o\'zgartirish uchun siz uning egasi bo\'lishingiz kerak.'

    def has_object_permission(self, request, view, obj):
        """
        Check if user is the owner of the object.
        Objects must have an 'owner', 'user', or 'manufacturer' attribute.
        """
        # Allow read access to anyone
        if request.method in SAFE_METHODS:
            return True

        # Write access: check if requesting user is the owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'manufacturer'):
            return obj.manufacturer == request.user
        
        # Default: deny write access
        return False


class IsOwner(BasePermission):
    """
    Allow access only to the owner of an object.
    No anonymous access.
    Used for personal resources (cart, orders, notifications, products).
    """

    message = 'Faqat bu resurssning egasi unga ruxsat olishi mumkin.'

    def has_object_permission(self, request, view, obj):
        """
        Check if user is the owner of the object.
        Objects must have a 'user', 'owner', or 'manufacturer' attribute.
        """
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'manufacturer'):
            return obj.manufacturer == request.user
        
        return False


class IsAuthenticatedAndActive(BasePermission):
    """
    Allow access only to authenticated users with is_active=True.
    Used on views that should block soft-deleted users.
    """

    message = 'Foydalanuvchi faolmas yoki autentifikatsiya qilinmagan.'

    def has_permission(self, request, view):
        """Check if user is authenticated and active."""
        return (
            bool(request.user and request.user.is_authenticated) and
            request.user.is_active
        )
