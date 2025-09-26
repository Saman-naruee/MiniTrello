import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend



class GoogleOauth2EmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        
        # Create credentials object from settings
        self.credentials = Credentials.from_authorized_user_info({
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "refresh_token": settings.GOOGLE_OAUTH_REFRESH_TOKEN,
        })
        
        # Build the Gmail service
        self.service = build('gmail', 'v1', credentials=self.credentials)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        
        count = 0
        for email_message in email_messages:
            try:
                message = self._build_mime_message(email_message)
                self.service.users().messages().send(userId='me', body=message).execute()
                count += 1
            except Exception as e:
                if not self.fail_silently:
                    raise e
        return count

    def _build_mime_message(self, email_message):
        # Using the body (which django-allauth populates with the text version)
        message = MIMEText(email_message.body)
        message['to'] = ", ".join(email_message.to)
        message['from'] = settings.GOOGLE_OAUTH_SENDER_EMAIL
        message['subject'] = email_message.subject
        
        # The message needs to be base64 encoded
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': encoded_message}
