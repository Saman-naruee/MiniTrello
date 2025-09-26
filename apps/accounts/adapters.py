import json
from django.contrib.auth import authenticate
from django.http import JsonResponse
from allauth.account.adapter import DefaultAccountAdapter
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from .models import User
import random
from django.utils.html import strip_tags
from allauth.utils import get_username_max_length
from apps.invitations.models import Invitation
from django.contrib import messages

# from premailer import transform  # pip install premailer (if you want to inline CSS)

class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter for account-related functionality, such as email confirmation.
    Extends DefaultAccountAdapter to customize email sending if needed.
    """
    
    def respond_user_inactive(self, request, user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'form': {'errors': {'__all__': ['This account is inactive.']}}
            })
        return super().respond_user_inactive(request, user)


    def send_mail(self, template_prefix, email, context):
        """
        Send an email using the provided template prefix.
        Matches allauth's default behavior: uses template_prefix directly (e.g., 'account/email/email_confirmation').
        """
        # Render subject (strip tags/HTML for plain text subject)
        subject = render_to_string(template_prefix + "_subject.txt", context, request=self.request).strip()
        subject = strip_tags(subject) if subject else ""
        
        # Render message (assume HTML; adjust if plain-text only)
        message = render_to_string(template_prefix + "_message.txt", context, request=self.request)
        
        # Use Django's mail send (or your custom logic, e.g., Anymail)
        from django.core.mail import EmailMultiAlternatives
        email_msg = EmailMultiAlternatives(
            subject,
            strip_tags(message),  # Plain text fallback
            self.get_from_email(),  # Or settings.DEFAULT_FROM_EMAIL
            [email],
        )
        email_msg.attach_alternative(message, "text/html")
        email_msg.send(fail_silently=False)


    def ajax_response(self, request, response, redirect_url=None, redirect_to=None, form=None, data=None, **kwargs):
        """
        Properly handle AJAX responses including redirects
        """
        if redirect_to:
            final_redirect = redirect_to
        else:
            final_redirect = redirect_url
            
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if isinstance(response, str):
                return JsonResponse({'redirect_location': response})
            if form and not form.is_valid():
                return JsonResponse({'form': {'errors': form.errors}})
            if final_redirect:
                return JsonResponse({'redirect': final_redirect})
            if data:
                return JsonResponse(data)
            return JsonResponse({'success': True})
        return response

    

    def get_login_redirect_url(self, request):
        url = super().get_login_redirect_url(request)
        # if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        #     return JsonResponse({'redirect_location': url})
        return url
    
    def save_user(self, request, user, form, commit=True):
        """
        This is called when a new user signs up.
        We override it to check for a pending invitation in the session.
        """
        # Call the parent method to save the user normally
        user = super().save_user(request, user, form, commit)
        # Override user creation for creating users superuser:
        user.is_superuser, user.is_staff = False, False
        invitation_token = request.session.pop('invitation_token', None)
        
        if invitation_token:
            try:
                # Find the pending invitation
                invitation = Invitation.objects.get(token=invitation_token, status=Invitation.STATUS_SENT)
                
                # Check if the new user's email matches the invitation's email
                if invitation.email.lower() == user.email.lower():
                    # Accept the invitation for the newly created user
                    invitation.accept(user)
                    messages.success(request, f"Welcome! You've successfully signed up and joined the board '{invitation.board.title}'.")
                else:
                    messages.warning(request, "You signed up with a different email than the one invited. Please accept the invitation again after logging in.")
            except Invitation.DoesNotExist:
                # The token was invalid, do nothing.
                pass
        
        return user
    
    def authenticate_by_username_or_email(self, request, username_or_email, password):
        """
        Authenticate user with either username or email.
        - User must provide either a username or email address.
        """
        try:
            # Try to authenticate with email first
            user = authenticate(
                request=request,
                username=username_or_email,
                password=password
            )
            
            # If not found by username, try to find user by email
            if user is None:
                try:
                    from .models import User
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(
                        request=request,
                        username=user_obj.username,
                        password=password
                    )
                except User.DoesNotExist:
                    pass
            
            return user
        except Exception:
            return None
    
    def clean_username(self, username, shallow=False):
        """
        Clean the username, handling the case where it might be empty.
        """
        username_max_length = get_username_max_length()
        username = super().clean_username(username, shallow=False)
        
        if not username:
            return None
            
        return username
    
    def populate_username(self, request, user):
        """
        Auto-populate username if not provided.
        """
        if not user.username and user.email:
            # Generate username from email if not provided
            base_username = user.email.split('@')[0]
            username = base_username
            counter = 1
            
            # Handle unique username constraint
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user.username = username
        return super().populate_username(request, user)


    def get_signup_redirect_url(self, request):
        """
        Return signup redirect URL
        """
        return super().get_signup_redirect_url(request)

    def respond_user_registered(self, request, user, form):
        """
        Handle response after user is registered
        """
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'redirect': self.get_login_redirect_url(request)
            })
        return super().respond_user_registered(request, user, form)
