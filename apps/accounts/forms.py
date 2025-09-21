from django import forms
from allauth.account.forms import LoginForm, SignupForm
from allauth.account.adapter import get_adapter

from .models import User

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


class CustomLoginForm(LoginForm):
    """
    Custom login form that allows login with either username or email.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['login'].widget.attrs.update({
            'placeholder': 'Username or Email',
            'class': 'form-control'
        })
    
    def clean_login(self):
        login = self.cleaned_data.get('login')
        if not login:
            raise forms.ValidationError('Please enter a username or email address.')
        return login

class CustomSignupForm(SignupForm):
    """
    Custom signup form that requires either username or email, but both are optional.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove required attribute from both fields
        self.fields['username'].required = False
        self.fields['email'].required = False
        
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Username (optional)',
            'class': 'form-control'
        })
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Email (optional)',
            'class': 'form-control'
        })
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        email = cleaned_data.get('email')
        
        # Require at least one of username or email
        if not username and not email:
            raise forms.ValidationError(
                'You must provide either a username or an email address.'
            )
        
        return cleaned_data
    
    def save(self, request):
        user = super().save(request)
        return user
