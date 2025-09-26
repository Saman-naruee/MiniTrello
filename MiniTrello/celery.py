import os
from celery import Celery
from decouple import config
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.development')

app = Celery('MiniTrello')

app.conf.broker_url = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
app.conf.result_backend = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
