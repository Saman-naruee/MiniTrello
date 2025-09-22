import re
from django import forms
from django.core.exceptions import ValidationError
try:
    from email_validator import validate_email, EmailNotValidError
except ImportError:
    # Fallback to basic validation if library not installed
    validate_email = None

# Alternative: Use py3-validate-email
try:
    from py3dnsbl import validate_email_domain
except ImportError:
    validate_email_domain = None

from apps.boards.models import Membership

class InvitationSendForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'})
    )

    def __init__(self, *args, **kwargs):
        self.board = kwargs.pop('board', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        """
        Comprehensive email validation using available third-party libraries
        or fallback validation.
        """
        email = self.cleaned_data['email'].lower().strip()
        domain = email.split('@')[1] if '@' in email else ''

        # Option 1: Use email-validator library (most comprehensive)
        if validate_email:
            try:
                # This validates format, checks domain existence, and more
                validated_email = validate_email(email, check_deliverability=True)
                email = validated_email.email
                domain = email.split('@')[1]
            except EmailNotValidError as e:
                raise forms.ValidationError(f'Invalid email address: {e}')

        # Option 2: Use py3-validate-email if available
        elif validate_email_domain:
            try:
                validate_email_domain(domain)
                # Additional format validation
                email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_regex, email):
                    raise forms.ValidationError('Invalid email format.')
            except Exception as e:
                raise forms.ValidationError('Unable to validate email address. Please check and try again.')

        else:
            # Fallback: Basic validation with common checks
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                raise forms.ValidationError('Please enter a valid email address.')

            if '..' in email or ' ' in email:
                raise forms.ValidationError('Email address cannot contain spaces or consecutive dots.')

            # Basic disposable domain check
            disposable_domains = {
                '10minutemail.com', 'tempmail.org', 'guerrillamail.com', 'mailinator.com',
                'temp-mail.org', 'throwaway.email', 'yopmail.com', 'tempemail.com'
            }
            if domain.lower() in disposable_domains:
                raise forms.ValidationError('Temporary or disposable email addresses are not allowed.')

        # Check if the user is already a member of the board
        if Membership.objects.filter(board=self.board, user__email__iexact=email).exists():
            raise forms.ValidationError('This user is already a member of this board.')

        return email

    def _check_mx_record(self, domain):
        """Helper method to check if domain has valid MX records."""
        import socket
        try:
            mx_records = socket.getmxrr(domain.lower())
            return bool(mx_records)
        except:
            return False
