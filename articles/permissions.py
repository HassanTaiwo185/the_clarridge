from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrSuperUserOrReadOnly(BasePermission):
    """
    Anyone (even anonymous) can read (GET/HEAD/OPTIONS).
    Only the article's uploader OR a superuser can update/delete it.
    """

    def has_permission(self, request, view):
        # Read access is open to everyone, including anonymous users
        if request.method in SAFE_METHODS:
            return True
        # Write access (create) requires authentication at minimum
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.uploaded_by == request.user or request.user.is_superuser