from rest_framework.permissions import BasePermission


class IsAdminOrSuperUserForManagement(BasePermission):
    """
    Anyone can submit a testimonial (POST).
    Only staff (admin) or superuser can list all statuses, update (approve/reject), or delete.
    Public read access to approved-only testimonials is handled separately via a public view.
    """

    def has_permission(self, request, view):
        if request.method == 'POST':
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )