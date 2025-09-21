from django.urls import reverse_lazy
from allauth.account.views import LoginView, SignupView
from .forms import CustomLoginForm, CustomSignupForm
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from allauth.account.authentication import get_authentication_records
from custom_tools.logger import custom_logger
from allauth.account.views import SignupView
from django.contrib.auth import login
from django.views.generic.edit import UpdateView

from .forms import ProfileUpdateForm
from .models import User



class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    A view for users to update their own profile information.
    """
    model = User
    form_class = ProfileUpdateForm
    template_name = 'account/profile_update.html'
    success_url = reverse_lazy('accounts:profile')  # Redirect to the profile page on success

    def get_object(self, queryset=None):
        """
        This method ensures that the user can only edit their own profile.
        """
        return self.request.user

    def form_valid(self, form):
        """
        Adds a success message after a successful update.
        """
        messages.success(self.request, 'Your profile has been updated successfully!')
        custom_logger(f"User {self.request.user.email} updated their profile: {self.request.user.first_name} {self.request.user.last_name}")
        
        # Let UpdateView handle saving and redirecting (avoids double-save)
        return super().form_valid(form)

class ProfileWebView(LoginRequiredMixin, TemplateView):
    """Web view for user profile page"""
    template_name = 'account/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context



class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'account/login.html'
    
    def form_valid(self, form):
        # Custom login logic if needed
        return super().form_valid(form)

class CustomSignupView(SignupView):
    form_class = CustomSignupForm
    template_name = 'account/signup.html'
    
    def form_valid(self, form):
        # Custom signup logic if needed
        return super().form_valid(form)
