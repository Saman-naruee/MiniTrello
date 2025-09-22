from django import forms
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
        Custom validation to check if the user is already a member of the board.
        """
        email = self.cleaned_data['email']
        if Membership.objects.filter(board=self.board, user__email=email).exists():
            raise forms.ValidationError('This user is already a member of this board.')
        return email
