from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied


class SuperuserRequiredMixin(AccessMixin):
    """
    Mixin to ensure that the user accessing the view is a superuser.
    If the user is not authenticated, they are redirected to the login page.
    If the user is authenticated but not a superuser, a PermissionDenied exception is raised (403).
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()  # Redirects to LOGIN_URL by default
        if not request.user.is_superuser:
            raise PermissionDenied("You do not have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)
