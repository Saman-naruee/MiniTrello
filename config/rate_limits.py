"""
Rate limiting utilities for production environment
"""

import time
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.conf import settings
from functools import wraps


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    pass


class RateLimiter:
    """Simple rate limiter using Django cache"""

    def __init__(self, key_prefix='rate_limit', window_seconds=60, max_requests=100):
        self.key_prefix = key_prefix
        self.window_seconds = window_seconds
        self.max_requests = max_requests

    def get_cache_key(self, identifier):
        """Generate cache key for identifier"""
        return f"{self.key_prefix}:{identifier}:{int(time.time() // self.window_seconds)}"

    def is_allowed(self, identifier):
        """Check if request is allowed within rate limits"""
        cache_key = self.get_cache_key(identifier)
        current_count = cache.get(cache_key, 0)

        if current_count >= self.max_requests:
            return False, current_count

        return True, current_count

    def increment(self, identifier):
        """Increment counter for identifier"""
        cache_key = self.get_cache_key(identifier)
        current_count = cache.get(cache_key, 0)

        # Set new count with expiration
        cache.set(cache_key, current_count + 1, self.window_seconds)

        return current_count + 1


def rate_limit(requests_per_minute=60, window_minutes=1):
    """
    Decorator for rate limiting views
    requests_per_minute: Maximum requests allowed per minute
    window_minutes: Time window for rate limiting
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            # Get identifier (user if authenticated, IP otherwise)
            if request.user.is_authenticated:
                identifier = f"user:{request.user.id}"
            else:
                identifier = f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"

            # Check rate limit
            limiter = RateLimiter(
                key_prefix=f"view_{view_func.__name__}",
                window_seconds=window_minutes * 60,
                max_requests=requests_per_minute
            )

            allowed, current_count = limiter.is_allowed(identifier)

            if not allowed:
                return HttpResponseForbidden(
                    f"Rate limit exceeded. Maximum {limiter.max_requests} requests per {window_minutes} minutes."
                )

            # Add rate limit headers
            response = view_func(request, *args, **kwargs)
            response['X-RateLimit-Limit'] = limiter.max_requests
            response['X-RateLimit-Remaining'] = max(0, limiter.max_requests - current_count - 1)
            response['X-RateLimit-Reset'] = int(time.time()) + limiter.window_seconds

            return response
        return wrapped
    return decorator


def check_sensitive_operation_rate_limit(user, operation_name, max_operations=5, window_minutes=10):
    """
    Check rate limit for sensitive operations like invitations, board creation, etc.

    Args:
        user: Django user instance
        operation_name: String identifier for the operation (e.g., 'send_invitation', 'create_board')
        max_operations: Maximum operations allowed in the time window
        window_minutes: Time window in minutes

    Returns:
        bool: True if allowed, False if rate limited
    """
    identifier = f"user:{user.id}:operation:{operation_name}"
    limiter = RateLimiter(
        key_prefix="sensitive_operation",
        window_seconds=window_minutes * 60,
        max_requests=max_operations
    )

    allowed, current_count = limiter.is_allowed(identifier)
    if allowed:
        limiter.increment(identifier)

    return allowed, current_count


# Pre-configured limiters for common operations
class OperationRateLimits:
    """Pre-configured rate limiters for common operations"""

    LOGIN_ATTEMPTS = RateLimiter('login_attempts', 60, 5)  # 5 attempts per minute
    SEND_INVITATION = RateLimiter('send_invitation', 600, 10)  # 10 invitations per 10 minutes
    CREATE_BOARD = RateLimiter('create_board', 300, 3)  # 3 boards per 5 minutes
    ADD_MEMBER = RateLimiter('add_member', 300, 5)  # 5 member additions per 5 minutes
    API_REQUEST = RateLimiter('api_request', 60, 100)  # 100 API requests per minute
