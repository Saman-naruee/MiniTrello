from django.urls import path
from .views import TestPageView


urlpatterns = [
    path("test/", TestPageView.as_view(), name="Test"),
]
