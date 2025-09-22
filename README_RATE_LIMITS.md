# Rate Limiting for Production

This guide documents the rate limiting features implemented for production deployment.

## Features

### 1. Middleware Rate Limiting
- **Automatic request limiting**: 100 requests per minute per user/IP
- **Protection against DoS attacks**
- **Suspicious request detection** (directory traversal, common exploits)

### 2. Sensitive Operation Rate Limiting
- **Invitation sending**: 10 invitations per 10 minutes per user
- **Login attempts**: 5 attempts per minute per IP/user
- **Board operations**: Configurable limits for board creation/modification
- **Member management**: Rate limits for adding/removing members

### 3. Rate Limiting Headers
All responses include standard rate limiting headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Timestamp when limit resets

## Configuration

Rate limits are configured in `config/production.py`:

```python
# Rate limiting settings
RATE_LIMIT_CONFIG = {
    'DEFAULT_REQUESTS_PER_MINUTE': 100,  # General API requests
    'LOGIN_ATTEMPTS_PER_MINUTE': 5,
    'BOARD_OPERATIONS_PER_MINUTE': 20,
    'INVITATION_OPERATIONS_PER_10_MINUTES': 10,
    'MEMBER_OPERATIONS_PER_5_MINUTES': 15,
}

# Rate limiting exemptions
RATE_LIMIT_EXEMPT_IPS = ['internal-ip-here']  # Allowlisted IPs
RATE_LIMIT_EXEMPT_USER_IDS = [1, 2, 3]  # Admin users exempt from limits
```

## Usage Examples

### 1. Decorator for View Rate Limiting

```python
from config.rate_limits import rate_limit

class MySensitiveView(LoginRequiredMixin, View):
    @rate_limit(requests_per_minute=30, window_minutes=5)  # 30 requests per 5 minutes
    def post(self, request):
        # Your view logic here
        pass
```

### 2. Manual Sensitive Operation Rate Limiting

```python
from config.rate_limits import check_sensitive_operation_rate_limit

def send_invitation(request):
    allowed, current_count = check_sensitive_operation_rate_limit(
        user=request.user,
        operation_name='send_invitation',
        max_operations=10,
        window_minutes=10
    )

    if not allowed:
        messages.error(request, "Rate limit exceeded for sending invitations.")
        return redirect('some_page')

    # Proceed with invitation sending
    pass
```

### 3. Pre-configured Limiters

```python
from config.rate_limits import OperationRateLimits

# Check login attempts
allowed, count = OperationRateLimits.LOGIN_ATTEMPTS.is_allowed(user_identifier)
if allowed:
    OperationRateLimits.LOGIN_ATTEMPTS.increment(user_identifier)

# Check invitation sending
allowed, count = OperationRateLimits.SEND_INVITATION.is_allowed(user_identifier)
if allowed:
    OperationRateLimits.SEND_INVITATION.increment(user_identifier)
```

## Monitoring and Alerts

The rate limiting system automatically:

1. **Logs rate limit violations** to Django's logging system
2. **Provides headers** for client applications to handle limits gracefully
3. **Blocks suspicious patterns** like directory traversal attempts
4. **Tracks attempts** per user and IP address

### Health Check Endpoint

Add a health check endpoint that monitoring systems can use:

```python
# In your main urls.py
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

@never_cache
def health_check(request):
    return JsonResponse({'status': 'healthy', 'timestamp': timezone.now().isoformat()})
```

### Alert Configuration

Monitor these metrics in production:

1. **Rate limit violations** - Spike may indicate attack
2. **Cache hit rates** - Ensure Redis is working properly
3. **Response times** - Rate limiting should not significantly impact performance
4. **Failed login attempts** - High numbers may indicate brute force attacks

## Troubleshooting

### Common Issues

1. **Rate limiting too restrictive**
   - Adjust limits in `RATE_LIMIT_CONFIG`
   - Add IPs/users to exemptions

2. **Cache performance issues**
   - Ensure Redis is properly configured
   - Monitor cache hit rates

3. **False positives with suspicious requests**
   - Check user agents and request patterns
   - Adjust suspicious patterns in middleware

### Debugging

To temporarily disable rate limiting:

```python
# Add to production.py temporarily
ENABLE_RATE_LIMITING = False
```

## Performance Considerations

- Rate limiting uses Django's cache framework
- Default is local memory cache (development)
- Production should use Redis for distributed rate limiting
- Minimal overhead per request when cache is fast

## Security Benefits

1. **Prevents brute force attacks** on login endpoints
2. **Limits spam/abuse** of invitation features
3. **Throttles automated attacks** on sensitive operations
4. **Protects against DoS attempts** on API endpoints
5. **Detects malicious patterns** in request data
