import json
from django.http import JsonResponse
from allauth.account.adapter import DefaultAccountAdapter
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
# from premailer import transform  # pip install premailer (if you want to inline CSS)

class CustomAccountAdapter(DefaultAccountAdapter):
    def respond_user_inactive(self, request, user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'form': {'errors': {'__all__': ['This account is inactive.']}}
            })
        return super().respond_user_inactive(request, user)


    def send_mail(self, template_prefix, email, context):
        """
        Sends an email using a custom template.
        """
        template_name = f"account/email/{template_prefix}.html"  # Correct template path
        subject = render_to_string(f"account/email/{template_prefix}_subject.txt", context)
        subject = subject.strip()
        body = render_to_string(template_name, context)

        # # Inline CSS (optional - requires premailer)
        # if 'premailer' in settings.INSTALLED_APPS:
        #     body = transform(body)

        message = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [email])
        message.content_subtype = "html"  # Set content type to HTML
        message.send()

    def ajax_response(self, request, response, redirect_url=None, form=None, data=None):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if isinstance(response, str):
                return JsonResponse({'redirect_location': response})
            if form and not form.is_valid():
                return JsonResponse({'form': {'errors': form.errors}})
            if redirect_url:
                return JsonResponse({'redirect': redirect_url})
            if data:
                return JsonResponse(data)
            return JsonResponse({'success': True})
        return response
    def get_login_redirect_url(self, request):
        url = super().get_login_redirect_url(request)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'redirect_location': url})
        return url
