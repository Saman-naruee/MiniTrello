from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user profile. Username is editable but required (no blanks).
    """
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
