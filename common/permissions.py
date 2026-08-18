# common/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOrSuperUserOrReadOnly(BasePermission):
    """
    Anyone (even anonymous) can read.
    Only staff (admin) or superuser can create/update/delete.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )