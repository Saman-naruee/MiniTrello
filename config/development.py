from .base import * # Import all base settings

# --- DEVELOPMENT-SPECIFIC SETTINGS ---

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Use SQLite for simple local development
SQLITE3 = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

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

try:
    PREFERRED_DB = config('PREFERRED_DB', cast=str)
    DATABASES = POSTGRES if PREFERRED_DB == 'postgres' else SQLITE3
except Exception as e:
    print(f"Error occurred while setting up databases: {e}")
    DATABASES = SQLITE3

# Use console backend for emails during development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS settings for local frontend development (e.g., React on port 3000)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
CORS_ALLOW_CREDENTIALS = True
