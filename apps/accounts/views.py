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
from django.urls import reverse_lazy
from allauth.account.authentication import get_authentication_records
from custom_tools.logger import custom_logger





User = get_user_model()

class ProfileView(APIView):
    """API view for user profile data"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'email': user.email,
            'date_joined': user.date_joined,
            'social_accounts': [
                {'provider': account.provider} 
                for account in getattr(user, 'socialaccount_set', {}).all()
            ]
        })

class ProfileWebView(LoginRequiredMixin, TemplateView):
    """Web view for user profile page"""
    template_name = 'account/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

@login_required
def profile_router(request):
    """Routes to either API or Web view based on settings"""
    if settings.IS_USE_API_FOR_PROFILE:
        # For API clients, redirect to API endpoint
        if request.headers.get('Accept') == 'application/json':
            return redirect('api-profile')
        # For web clients requesting API data
        elif settings.PREFFERED_IMPLEMENTATION_FOR_PROJECT_API_OR_WEBPAGES == 'API':
            return redirect('api-profile')
    
    # Default to web view
    return redirect('web-profile')

class LogoutSuccessView(TemplateView):
    """View shown after successful logout"""
    template_name = 'account/logout_success.html'

class LoginView(TemplateView):
    """Custom login view that handles both normal and social auth"""
    template_name = 'account/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context needed for the login page
        return context

class RegisterView(TemplateView):
    """Custom registration view"""
    template_name = 'account/register.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context needed for the registration page
        return context


from allauth.account.views import SignupView
from django.contrib.auth import login

class CustomSignupView(SignupView):
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.user)
        return response
