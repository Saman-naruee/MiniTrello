from django.urls import path
from . import views

urlpatterns = [
    # API endpoint
    path('api/profile/', views.ProfileView.as_view(), name='api-profile'),
    
    # Web endpoints
    path('profile/', views.profile_router, name='profile'),
    path('profile/web/', views.ProfileWebView.as_view(), name='web-profile'),
    path('login/', views.LoginView.as_view(), name='custom-login'),
    path('register/', views.RegisterView.as_view(), name='custom-register'),
    path('logout/success/', views.LogoutSuccessView.as_view(), name='logout-success'),
    path('signup/', views.CustomSignupView.as_view(), name='account_signup'),
]
