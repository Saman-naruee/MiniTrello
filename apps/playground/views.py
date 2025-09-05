from django.shortcuts import render
from django.views.generic import ListView
from apps.accounts.models import User


class TestPageView(ListView):
    template_name = 'test.html'
    queryset = User.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['name'] = self.queryset.filter(username=self.request.user.username)
        return context
