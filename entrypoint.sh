#!/bin/bash
# Django entrypoint script to handle migrations automatically

# Wait for the database to be ready
echo "Waiting for database to be ready..."
sleep 10

# Navigate to the app directory
cd /app

# Run makemigrations (detects any new model changes)
echo "Running makemigrations..."
python manage.py makemigrations

# Apply migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Create superuser if DJANGO_SUPERUSER_USERNAME is set
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "Creating superuser if doesn't exist..."
    echo "from apps.accounts.models import User; User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists() or User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')" | python manage.py shell
fi

# Install gunicorn
echo "Installing gunicorn..."
pip install gunicorn

# Execute the command passed as arguments (e.g., gunicorn)
echo "Starting Django application..."
exec "$@"
