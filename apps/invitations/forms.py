import re
from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from apps.boards.models import Membership

User = get_user_model()

class InvitationSendForm(forms.Form):
    """
    Form for sending board invitations.
    Validates email and ensures the invitee is not already a board member.
    """
    email = forms.EmailField(
        label=_('Invitee Email'),
        required=True,
        help_text=_('Enter the email address of the person to invite.')
    )

    def __init__(self, *args, board=None, **kwargs):
        """
        Initialize with the board instance for validation.
        """
        super().__init__(*args, **kwargs)
        self.board = board

    def clean_email(self):
        """
        Custom validation: Check if the email corresponds to an existing board member.
        Allows inviting new users (no User exists) or non-members.
        """
        email = self.cleaned_data['email']
        if not self.board:
            raise forms.ValidationError(
                _('Board context is required for validation.'),
                code='invalid_board'
            )

        # Check for existing membership by email (case-insensitive)
        if Membership.objects.filter(
            user__email__iexact=email,
            board=self.board
        ).exists():
            raise forms.ValidationError(
                _('This user is already a member of this board.'),
                code='already_member'
            )

        return email
