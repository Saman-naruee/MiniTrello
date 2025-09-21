from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class FlexibleAuthenticationBackend(ModelBackend):
    """
    Authentication backend that allows login with either username or email.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        try:
            # First try to get user by username
            user = User.objects.get(Q(username=username) | Q(email=username))
            
            # Check if the user can authenticate with the given password
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # Handle edge case where both username and email match
            user = User.objects.filter(
                Q(username=username) | Q(email=username)
            ).first()
            if user and user.check_password(password) and self.user_can_authenticate(user):
                return user
        
        return None
