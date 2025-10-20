# Use standard Python image (Render supports Docker Hub)
FROM python:3.11-slim

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

# Create startup script for Render deployment
RUN echo '#!/bin/bash\nset -e\necho "Starting Django application..."\necho "Running database migrations..."\npython manage.py migrate --noinput\necho "Collecting static files..."\npython manage.py collectstatic --noinput\necho "Creating superuser (if needed)..."\npython manage.py create_superuser || echo "Superuser creation skipped"\necho "Starting gunicorn on port $PORT"\nexec gunicorn mangoAPI.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120 --log-level info --access-logfile - --error-logfile -' > /app/start.sh
RUN chmod +x /app/start.sh

# Expose port
EXPOSE $PORT

# Use the startup script
CMD ["/app/start.sh"]