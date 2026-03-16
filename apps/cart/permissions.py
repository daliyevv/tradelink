from rest_framework.permissions import BasePermission


class IsCartOwner(BasePermission):
    """
    Permission to check if user is the owner of the cart.
    """

    message = "You don't have permission to access this cart."

    def has_object_permission(self, request, view, obj):
        """Check if the userrequest is the owner of the cart."""
        return obj.owner == request.user
