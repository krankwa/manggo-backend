#!/bin/bash
set -ex  # Enable debugging and exit on error

echo "================================="
echo "Starting Django Application"
echo "================================="
echo "PORT environment variable: ${PORT:-NOT SET}"
echo "Using port: ${PORT:-8000}"

# Ensure PORT is set
export PORT=${PORT:-8000}

echo "Running migrations..."
python manage.py migrate --noinput
echo "Migrations complete - SUCCESS"

echo "Starting Gunicorn on 0.0.0.0:$PORT"
exec gunicorn mangoAPI.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 4 \
    --timeout 300 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
