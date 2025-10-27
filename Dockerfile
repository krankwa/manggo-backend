# Use standard Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=mangoAPI.settings
ENV PORT=8000

# Install system dependencies including OpenGL for OpenCV/TensorFlow
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libhdf5-dev \
        pkg-config \
        libgl1-mesa-glx \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Use shell form to properly expand $PORT variable
CMD python manage.py migrate --noinput && \
    echo "Starting gunicorn on port $PORT..." && \
    gunicorn mangoAPI.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 4 \
    --timeout 300 \
    --log-level debug \
    --access-logfile - \
    --error-logfile - \
    --capture-output