# Temporary fix: Use public Python image during Docker Hub outage
FROM public.ecr.aws/docker/library/python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE=mangoAPI.settings

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libhdf5-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Copy the rest of the application
COPY . .

# Test if Django can start
RUN python manage.py check --deploy

# Collect static files
RUN python manage.py collectstatic --noinput

# Create a simple startup script for Railway deployment
RUN echo '#!/bin/bash\nset -e\necho "Starting mangosense backend for Railway..."\n\n# Skip migrations on Railway - handle them separately\necho "Environment: Railway deployment"\necho "Port: $PORT"\necho "Database URL configured: $([ -n \"$DATABASE_URL\" ] && echo \"Yes\" || echo \"No - using SQLite\")"\n\n# Start gunicorn directly\necho "Starting gunicorn on port $PORT"\nexec gunicorn mangoAPI.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 300 --log-level info --access-logfile - --error-logfile -' > /app/start.sh
RUN chmod +x /app/start.sh

# Expose port
EXPOSE $PORT

# Use the startup script
CMD ["/app/start.sh"]