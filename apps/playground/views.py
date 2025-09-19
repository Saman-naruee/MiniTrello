from django.shortcuts import render
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.accounts.models import User


class TestPageView(LoginRequiredMixin, ListView):
    template_name = 'test.html'
    queryset = User.objects.all()
    permission_denied_message = "You must be logged in to view this page."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['name'] = self.queryset.filter(username=self.request.user.username)
        return context
