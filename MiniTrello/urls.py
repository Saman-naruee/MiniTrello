"""
URL configuration for MiniTrello project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.views.i18n import set_language

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API authentication endpoints
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    
    # Google login and social auth
    path('accounts/', include('allauth.urls')),
    
    # Custom accounts views
    path('account/', include('apps.accounts.urls')),
    
    # Boards pages (template-based with htmx)
    path('boards/', include('apps.boards.urls')),
    
    # i18n - Language selection
    path('i18n/setlang/', set_language, name='set_language'),
    
    # Home page
    path('', login_required(TemplateView.as_view(template_name='home.html')), name='Home')
]
