"""
Custom middleware for production environment
"""

import time
from django.core.cache import cache
from django.http import HttpResponseTooManyRequests
from django.utils.deprecation import MiddlewareMixin
from .rate_limits import RateLimiter


class RateLimitMiddleware(MiddlewareMixin):
    """
    Middleware for rate limiting requests in production.
    Only active when DEBUG=False and ENABLE_RATE_LIMITING=True.
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.rate_limiter = RateLimiter(
            key_prefix='middleware_request',
            window_seconds=60,
            max_requests=100
        )

    def process_request(self, request):
        from django.conf import settings

        # Only apply rate limiting in production
        if getattr(settings, 'DEBUG', False) or not getattr(settings, 'ENABLE_RATE_LIMITING', False):
            return None

        # Skip rate limiting for exempt IPs
        client_ip = request.META.get('REMOTE_ADDR', '')
        exempt_ips = getattr(settings, 'RATE_LIMIT_EXEMPT_IPS', [])
        if client_ip in exempt_ips:
            return None

        # Skip rate limiting for admin users if exempt user IDs are configured
        if hasattr(request, 'user') and request.user.is_authenticated:
            exempt_user_ids = getattr(settings, 'RATE_LIMIT_EXEMPT_USER_IDS', [])
            if request.user.id in exempt_user_ids:
                return None

        # Skip rate limiting for health checks and static files
        path = request.path
        if any(path.startswith(prefix) for prefix in ['/admin/', '/static/', '/media/', '/health/']):
            return None

        # Determine identifier for rate limiting
        if hasattr(request, 'user') and request.user.is_authenticated:
            identifier = f"user:{request.user.id}"
        else:
            identifier = f"ip:{client_ip}"

        # Check rate limit
        allowed, current_count = self.rate_limiter.is_allowed(identifier)

        if not allowed:
            return HttpResponseTooManyRequests(
                content="Rate limit exceeded. Please try again later.",
                content_type="text/plain"
            )

        # Add rate limit headers to response
        request._rate_limit_headers = {
            'X-RateLimit-Limit': self.rate_limiter.max_requests,
            'X-RateLimit-Remaining': max(0, self.rate_limiter.max_requests - current_count - 1),
            'X-RateLimit-Reset': int(time.time() + self.rate_limiter.window_seconds),
        }

    def process_response(self, request, response):
        # Add rate limit headers to successful responses
        if hasattr(request, '_rate_limit_headers'):
            headers = request._rate_limit_headers
            response['X-RateLimit-Limit'] = headers['X-RateLimit-Limit']
            response['X-RateLimit-Remaining'] = headers['X-RateLimit-Remaining']
            response['X-RateLimit-Reset'] = headers['X-RateLimit-Reset']

        return response


class SuspiciousRequestMiddleware(MiddlewareMixin):
    """
    Middleware to detect and block suspicious requests
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.suspicious_patterns = [
            '../',  # Directory traversal attempts
            'etc/passwd',
            'wp-admin',  # WordPress scanning
            'phpmyadmin',
        ]

    def process_request(self, request):
        from django.conf import settings
        if getattr(settings, 'DEBUG', False):
            return None

        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        path = request.path.lower()
        query = request.META.get('QUERY_STRING', '').lower()

        # Check for suspicious patterns
        suspicious_content = user_agent + ' ' + path + ' ' + query
        for pattern in self.suspicious_patterns:
            if pattern in suspicious_content:
                # Log suspicious activity
                from django.core.cache import cache
                suspicious_key = f"suspicious:{request.META.get('REMOTE_ADDR', '')}"

                # Track suspicious attempts
                attempts = cache.get(suspicious_key, 0)
                cache.set(suspicious_key, attempts + 1, 300)  # 5 minute window

                # Block if too many suspicious attempts
                if attempts > 3:
                    return HttpResponseTooManyRequests(
                        "Too many suspicious requests detected."
                    )

                break
