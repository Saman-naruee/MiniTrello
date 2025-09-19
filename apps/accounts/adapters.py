import json
from django.http import JsonResponse
from allauth.account.adapter import DefaultAccountAdapter
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from .models import User
from django.shortcuts import redirect
from django.urls import reverse
import random
from allauth.account import app_settings

# from premailer import transform  # pip install premailer (if you want to inline CSS)

class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to override default allauth behavior
    """
    def pre_authenticate(self, request, **credentials):
        # Override to remove rate limiting temporarily if needed
        pass

    def is_open_for_signup(self, request):
        """
        Check if the email exists and redirect to login if it does
        """
        if request.method == "POST":
            email = request.POST.get("email")
            if email and User.objects.filter(email=email).exists():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'redirect': reverse('account_login'),
                        'message': 'This email is already registered. Please login.'
                    })
                return redirect('account_login')
        return True

    def respond_user_inactive(self, request, user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'form': {'errors': {'__all__': ['This account is inactive.']}}
            })
        return super().respond_user_inactive(request, user)


    def send_mail(self, template_prefix, email, context):
        if template_prefix == "account/email/email_confirmation_signup":
            template_prefix = "email_confirmation_signup"
        template_name = f"account/email/{template_prefix}.html"
        subject = render_to_string(f"account/email/{template_prefix}_subject.txt", context)
        subject = subject.strip()
        body = render_to_string(template_name, context)
        message = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [email])
        message.content_subtype = "html"
        message.send()

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
        data = form.cleaned_data
        email = data.get('email')
        username = data.get('username')
        password = data.get('password1')

        if not email and username:
            # If registering with username only
            user.username = username
            if User.objects.filter(username=username).exists():
                user.username = f"{username}{random.randint(1, 100000)}"
        elif email and not username:
            # If registering with email
            username = email.split('@')[0]
            user.username = username
            if User.objects.filter(username=username).exists():
                user.username = f"{username}{random.randint(1, 100000)}"
            user.email = email

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.is_staff = False
        user.is_superuser = False

        if commit:
            user.save()
        return user

    def authenticate(self, request, **credentials):
        # Allow authentication with username/password without email
        if 'username' in credentials and 'password' in credentials:
            return super().authenticate(request, **credentials)
        return super().authenticate(request, **credentials)
