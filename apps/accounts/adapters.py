import json
from django.http import JsonResponse
from allauth.account.adapter import DefaultAccountAdapter
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from .models import User
import random
from django.utils.html import strip_tags

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
        if redirect_to:
            final_redirect = redirect_to
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
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'redirect_location': url})
        return url
    
    def save_user(self, request, user, form, commit=True):
        """
        Customize user saving during signup (e.g., auto-set profile fields).
        """
        user = super().save_user(request, user, form, commit=False)
        email = user.email
        username = email.split('@')[0]
        if '@' in email:
            user.username = username
            if User.objects.filter(username=username):
                user.username = f"{username}{random.randint(1, 100000)}"
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user
