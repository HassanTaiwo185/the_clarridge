from rest_framework.permissions import BasePermission


class IsAdminOrSuperUserForManagement(BasePermission):
    """
    Anyone can submit an application (POST — no read access for the public).
    Only staff (admin) or superuser can list, view, update, or delete applications.
    """

    def has_permission(self, request, view):
        if request.method == 'POST':
            return True  # public application form
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )