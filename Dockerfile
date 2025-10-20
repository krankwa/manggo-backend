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

# Create a debug startup script for Railway deployment
RUN echo '#!/bin/bash\nset -e\necho "=== Railway Startup Debug Info ==="\necho "Environment: $RAILWAY_ENVIRONMENT_NAME"\necho "Port: $PORT"\necho "Python version: $(python --version)"\necho "Working directory: $(pwd)"\necho "Files in current directory:"\nls -la\necho "Django check:"\npython manage.py check --verbosity=2 || echo "Django check failed but continuing..."\necho "Testing simple Django command:"\npython -c "import django; print(f\\"Django version: {django.get_version()}\\")" || echo "Django import failed"\necho "Testing settings import:"\npython -c "from mangoAPI import settings; print(\\"Settings imported successfully\\")" || echo "Settings import failed"\necho "=== Starting Gunicorn ==="\necho "Starting gunicorn on 0.0.0.0:$PORT"\nexec gunicorn mangoAPI.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 300 --log-level debug --access-logfile - --error-logfile - --capture-output --enable-stdio-inheritance' > /app/start.sh
RUN chmod +x /app/start.sh

# Expose port
EXPOSE $PORT

# Use the startup script
CMD ["/app/start.sh"]