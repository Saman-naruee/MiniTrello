import base64
import json
import os
import smtplib
from email.message import EmailMessage as StdlibEmailMessage  # for SMTP sending
from django.template.loader import render_to_string
from django.conf import settings
from django.http import JsonResponse
from allauth.account.adapter import DefaultAccountAdapter
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Environment / settings expected:
# - GOOGLE_OAUTH_CREDENTIALS_JSON: path to OAuth client credentials JSON (optional if using token file stored with client_id/secret)
# - GMAIL_TOKEN_FILE: path to token JSON (contains refresh_token)
# - EMAIL_FROM: fallback email sender or use settings.DEFAULT_FROM_EMAIL

GMAIL_TOKEN_FILE = getattr(settings, "GMAIL_TOKEN_FILE", os.environ.get("GMAIL_TOKEN_FILE", "gmail_token.json"))
SMTP_HOST = getattr(settings, "GMAIL_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = getattr(settings, "GMAIL_SMTP_PORT", 587)  # STARTTLS recommended

def get_gmail_credentials():
    """
    Load stored token JSON and return a google.oauth2.credentials.Credentials object.
    The token JSON must include refresh_token, client_id, client_secret, token_uri (https://oauth2.googleapis.com/token)
    If access token expired, refresh automatically.
    """
    if not os.path.exists(GMAIL_TOKEN_FILE):
        raise FileNotFoundError(f"Gmail token file not found: {GMAIL_TOKEN_FILE}. Run get_gmail_token.py first.")
    with open(GMAIL_TOKEN_FILE, "r") as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", ["https://mail.google.com/"]),
    )

    # Refresh if needed
    if not creds.valid and creds.refresh_token:
        request = Request()
        creds.refresh(request)
        # Save refreshed token back to file (update access token)
        new_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        with open(GMAIL_TOKEN_FILE, "w") as f:
            json.dump(new_data, f)
    return creds

def generate_xoauth2_string(username, access_token):
    """
    Create XOAUTH2 auth string for SMTP:
    base64("user=<email>\x01auth=Bearer <access_token>\x01\x01")
    """
    auth_string = f"user={username}\x01auth=Bearer {access_token}\x01\x01"
    return base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

class CustomAccountAdapter(DefaultAccountAdapter):
    """
    To override default allauth behavior and send mail via Gmail SMTP using OAuth2.
    """
    def respond_user_inactive(self, request, user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'form': {'errors': {'__all__': ['This account is inactive.']}}
            })
        return super().respond_user_inactive(request, user)

    def send_mail(self, template_prefix, email, context):
        """
        Compose the message using existing templates and send via SMTP with OAuth2.
        """
        if template_prefix == "account/email/email_confirmation_signup":
            template_prefix = "email_confirmation_signup"
        template_name = f"account/email/{template_prefix}.html"
        subject = render_to_string(f"account/email/{template_prefix}_subject.txt", context).strip()
        body = render_to_string(template_name, context)

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_FROM", None)
        if not from_email:
            raise ValueError("DEFAULT_FROM_EMAIL (or EMAIL_FROM) must be set in Django settings.")

        # Build MIME message
        msg = StdlibEmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = email
        msg.set_content("This is an HTML email. If you see this, your client does not support HTML.")
        msg.add_alternative(body, subtype="html")

        # Send via Gmail SMTP with OAuth2
        creds = get_gmail_credentials()
        access_token = creds.token
        if not access_token:
            # Force refresh if token field was empty
            request = Request()
            creds.refresh(request)
            access_token = creds.token

        auth_string = generate_xoauth2_string(from_email, access_token)

        # Connect and authenticate
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            # Use AUTH XOAUTH2
            # smtp.auth() helper isn't available with XOAUTH2 by default; use .docmd
            auth_command = "AUTH XOAUTH2 " + auth_string
            code, resp = server.docmd(auth_command)
            if code != 235:
                # 235 = Authentication successful
                raise Exception(f"SMTP AUTH XOAUTH2 failed: {code} {resp}")
            server.send_message(msg)

    def ajax_response(self, request, response, redirect_url=None, redirect_to=None, form=None, data=None, **kwargs):
        final_redirect = redirect_to or redirect_url
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
        user = super().save_user(request, user, form, commit=False)
        email = user.email
        if '@' in email:
            user.username = email.split('@')[0]
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user
