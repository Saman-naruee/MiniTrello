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

# Use console backend for emails during development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'config.email_backend.GoogleOauth2EmailBackend'

# CORS settings for local frontend development (e.g., React on port 3000)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
CORS_ALLOW_CREDENTIALS = True

import os
from decouple import config

# Site base URL for absolute links (e.g., invitation emails)
BASE_URL = config('BASE_URL', default='http://localhost:8000')

# Celery configuration (ensure env overrides defaults)
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# For dev: Eager mode for tests/sync (disable for real async)
CELERY_TASK_ALWAYS_EAGER = True  # Set False in production.py
CELERY_TASK_EAGER_PROPAGATES = True
