from .base import * # Import all base settings

# --- DEVELOPMENT-SPECIFIC SETTINGS ---

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# Use SQLite for simple local development
SQLITE3 = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Define POSTGRES only if preferred (avoids config reads on import if using SQLite)
POSTGRES = None
try:
    PREFERRED_DB = config('PREFERRED_DB', default='postgres', cast=str)
    if PREFERRED_DB == 'postgres':
        POSTGRES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': config('DB_NAME', cast=str),
                'USER': config('DB_USER', cast=str),
                'PASSWORD': config('DB_PASSWORD', cast=str),
                'HOST': config('DB_HOST', cast=str),
                'PORT': config('DB_PORT', cast=str),
            }
        }
    DATABASES = POSTGRES if PREFERRED_DB == 'postgres' else SQLITE3
except Exception as e:
    print(f"Error occurred while setting up databases: {e}")
    DATABASES = SQLITE3

import os

# Celery Configuration (env-driven for Docker/local flexibility)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)  # Same as broker
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 5

# Dev: Eager execution for sync testing (disable in prod)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Site base URL for emails/links (env-driven)
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8000')

# Email for dev (console logging; override in .env for SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS settings for local frontend development (e.g., React on port 3000)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
CORS_ALLOW_CREDENTIALS = True
