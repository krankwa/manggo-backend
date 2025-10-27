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

# Make startup script executable
RUN chmod +x /app/start.sh

# Check if model files are valid (not LFS pointers)
RUN python check_models.py || echo "WARNING: Model files may not be properly downloaded"

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Run start.sh directly without bash wrapper for testing
CMD ["/app/start.sh"]