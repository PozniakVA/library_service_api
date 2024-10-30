from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminUserOrIsAuthenticatedReadOnly(BasePermission):
    """
    The request is authenticated as a user, or is a read-only request.
    """

    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS
            and request.user.is_authenticated
            or request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )


class IsAdminUserOnly:
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )