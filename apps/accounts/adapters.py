from allauth.account.adapter import DefaultAccountAdapter
import json
from django.http import JsonResponse

class CustomAccountAdapter(DefaultAccountAdapter):
    def ajax_response(self, request, response, redirect_url=None, form=None, data=None):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if form and not form.is_valid():
                return JsonResponse({'form': {'errors': form.errors}})
            if redirect_url:
                return JsonResponse({'redirect': redirect_url})
            if data: 
                return JsonResponse(data)
            return JsonResponse({'success': True})
        return response
