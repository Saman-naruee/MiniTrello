from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    
    # Web endpoints
    path('profile/', views.ProfileWebView.as_view(), name='profile'),
    
    # The URL for the profile update view.
    path('profile/update/', views.ProfileUpdateView.as_view(), name='profile_update'),

    # # API endpoint
    # path('api/profile/', views.ProfileView.as_view(), name='api-profile'),
    # path('profile/', views.profile_router, name='profile'),

    # # You might not need these custom login/register views if you use allauth's templates
    # path('login/', views.LoginView.as_view(), name='custom-login'),
    # path('register/', views.RegisterView.as_view(), name='custom-register'),
    
    # path('logout/success/', views.LogoutSuccessView.as_view(), name='logout-success'),
    
    # # This overrides the default allauth signup view if needed
    # path('signup/', views.CustomSignupView.as_view(), name='account_signup'),
    
]
