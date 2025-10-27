#!/bin/bash
set -e

echo "================================="
echo "Starting Django Application"
echo "================================="

# Ensure PORT is set
export PORT=${PORT:-8000}
echo "Server will bind to: 0.0.0.0:$PORT"

# Run database migrations
echo "Running migrations..."
python manage.py migrate --noinput
echo "Migrations complete"

# Start Gunicorn server
echo "Starting Gunicorn..."
exec gunicorn mangoAPI.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 4 \
    --timeout 300 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
