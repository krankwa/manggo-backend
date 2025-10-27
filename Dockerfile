# Use standard Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=mangoAPI.settings
ENV PORT=8000

# Install system dependencies including Git LFS for model files
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libhdf5-dev \
        pkg-config \
        libgl1 \
        libglib2.0-0 \
        git \
        git-lfs \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Initialize Git LFS
RUN git lfs install

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Check if model files are valid (not LFS pointers)
RUN python check_models.py || echo "WARNING: Model files may not be properly downloaded"

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Create a startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "================================="\n\
echo "Starting Django Application"\n\
echo "================================="\n\
echo "PORT environment variable: ${PORT:-NOT SET}"\n\
echo "Using port: ${PORT:-8000}"\n\
export PORT=${PORT:-8000}\n\
echo "Running migrations..."\n\
python manage.py migrate --noinput\n\
echo "Migrations complete"\n\
echo "Starting Gunicorn on 0.0.0.0:$PORT"\n\
exec gunicorn mangoAPI.wsgi:application \\\n\
    --bind 0.0.0.0:$PORT \\\n\
    --workers 1 \\\n\
    --threads 4 \\\n\
    --timeout 300 \\\n\
    --log-level info \\\n\
    --access-logfile - \\\n\
    --error-logfile -' > /app/start.sh && chmod +x /app/start.sh

# Use the startup script
CMD ["/bin/bash", "/app/start.sh"]