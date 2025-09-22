from .base import * # Import all base settings
from .rate_limits import RateLimiter, OperationRateLimits, rate_limit, check_sensitive_operation_rate_limit

# --- PRODUCTION-SPECIFIC SETTINGS ---

DEBUG = False

# --- RATE LIMITING SETTINGS ---

# Enable rate limiting middleware for production
MIDDLEWARE = MIDDLEWARE + [
    'config.middleware.RateLimitMiddleware',
]

# Cache settings for rate limiting (already configured for production with Redis/Celery)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',  # Fallback to local memory
    }
}

# Try to use Redis for better performance if available
try:
    CACHES['default'] = {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
except ImportError:
    pass  # Fall back to local memory cache

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    'DEFAULT_REQUESTS_PER_MINUTE': 100,  # General API requests
    'LOGIN_ATTEMPTS_PER_MINUTE': 5,
    'BOARD_OPERATIONS_PER_MINUTE': 20,
    'INVITATION_OPERATIONS_PER_10_MINUTES': 10,
    'MEMBER_OPERATIONS_PER_5_MINUTES': 15,
}

# Rate limiting enabled only in production
ENABLE_RATE_LIMITING = True

# Rate limiting exemptions (allowlist for internal IPs, admin users, etc.)
RATE_LIMIT_EXEMPT_IPS = config('RATE_LIMIT_EXEMPT_IPS', default='').split(',') if config('RATE_LIMIT_EXEMPT_IPS', default='') else []
RATE_LIMIT_EXEMPT_USER_IDS = [int(uid) for uid in config('RATE_LIMIT_EXEMPT_USER_IDS', default='').split(',') if uid.strip().isdigit()]

# Replace with your actual domain name(s)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

# Use PostgreSQL for production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', cast=int),
    }
}

# Production email backend (example using SMTP, you'll replace this for Google OAuth)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

# Security settings for production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000 # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


EMAIL_BACKEND = 'config.email_backend.GoogleOauth2EmailBackend'

