from rest_framework import permissions


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Anyone can browse (GET). Only staff (the single vendor's own team)
    can create/update/delete products - guest checkout browsing needs
    no write access at all.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)
