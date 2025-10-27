# Railway Deployment Documentation

## Overview
This document outlines the successful deployment of the MangoSense Django backend API with TensorFlow machine learning models to Railway.app using Docker.

---

## Deployment Architecture

### Technology Stack
- **Backend Framework**: Django 5.2.4
- **ML Framework**: TensorFlow 2.19.0
- **Models**: MobileNetV2 (Leaf & Fruit Detection)
- **Web Server**: Gunicorn
- **Container**: Docker (Python 3.11-slim)
- **Platform**: Railway.app

### Key Components
1. **Dockerfile**: Defines the container build process
2. **start.sh**: Startup script for migrations and Gunicorn
3. **check_models.py**: Validates ML model files during build
4. **railway.json**: Railway-specific configuration
5. **requirements.txt**: Python dependencies

---

## Critical Deployment Decisions

### 1. Model Storage Solution
**Problem**: ML model files (9-10 MB each) were initially stored using Git LFS, which Railway couldn't pull during deployment.

**Solution**: Removed Git LFS tracking and committed model files directly to the repository.

```bash
git lfs untrack '*.keras'
git rm --cached models/*.keras
git add models/*.keras
git commit -m "Remove models from LFS and commit directly"
```

**Why**: Railway's Docker build process doesn't have access to Git LFS credentials, resulting in 0-byte model files.

---

### 2. Deployment Configuration Priority
**Problem**: Multiple deployment configuration files (Dockerfile, Procfile, nixpacks.toml) conflicted, causing Railway to ignore the Dockerfile CMD.

**Solution**: 
- Removed `Procfile` and `nixpacks.toml`
- Used only `Dockerfile` with `railway.json` set to `"builder": "DOCKERFILE"`
- Created `start.sh` as a separate executable file (not inline script)

**Why**: Railway's build system prioritizes Procfile over Dockerfile CMD. Using only Dockerfile ensures predictable behavior.

---

### 3. Startup Script Design
**Problem**: Inline bash scripts in Dockerfile had issues with:
- Line ending conversions (CRLF vs LF on Windows)
- Command escaping and quoting
- Environment variable expansion

**Solution**: Created `start.sh` as a separate file:

```bash
#!/bin/bash
set -e

# Ensure PORT is set
export PORT=${PORT:-8000}

# Run migrations
python manage.py migrate --noinput

# Start Gunicorn
exec gunicorn mangoAPI.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 4 \
    --timeout 300 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
```

**Why**: Separate file ensures proper line endings and cleaner code organization.

---

### 4. Gunicorn Configuration
**Key Settings**:
- `--workers 1`: Single worker to minimize memory usage (ML models are memory-intensive)
- `--threads 4`: Handle multiple concurrent requests efficiently
- `--timeout 300`: 5-minute timeout for ML inference operations
- `--bind 0.0.0.0:$PORT`: Railway dynamically assigns PORT

**Why**: TensorFlow models consume significant memory. Single worker with multiple threads balances performance and resource constraints.

---

## Dockerfile Structure

```dockerfile
FROM python:3.11-slim

# Environment setup
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=mangoAPI.settings
ENV PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential libhdf5-dev pkg-config \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Prepare application
RUN chmod +x /app/start.sh
RUN python check_models.py
RUN python manage.py collectstatic --noinput

# Run startup script
CMD ["/app/start.sh"]
```

### Build Optimizations
1. **Layer Caching**: Dependencies copied before application code
2. **Multi-Stage**: System packages installed separately
3. **Model Validation**: `check_models.py` ensures files aren't LFS pointers
4. **Static Files**: Collected during build, not runtime

---

## Django Settings for Production

### CORS Configuration
```python
CORS_ALLOW_ALL_ORIGINS = True  # For mobile app compatibility
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8100",  # Ionic dev
    "capacitor://localhost",  # Mobile app
    "ionic://localhost",
]
```

### Static Files (Whitenoise)
```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files
    # ... other middleware
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### Security Settings
```python
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = ['*']  # Railway manages domains
SECRET_KEY = os.environ.get('SECRET_KEY', 'default-key')
```

---

## Railway Configuration

### railway.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Environment Variables (Set in Railway Dashboard)
```
DEBUG=False
SECRET_KEY=<your-production-secret-key>
CORS_ALLOW_ALL_ORIGINS=True
PORT=<auto-assigned-by-railway>
```

---

## Deployment Process

### Step 1: Prepare Repository
```bash
# Ensure models are committed directly (not LFS)
git add models/*.keras
git commit -m "Add model files"

# Remove conflicting deployment files
rm Procfile nixpacks.toml

# Commit final configuration
git add Dockerfile start.sh railway.json
git commit -m "Finalize Railway deployment configuration"
git push origin main
```

### Step 2: Railway Setup
1. Create new project on Railway.app
2. Connect GitHub repository
3. Railway auto-detects Dockerfile
4. Set environment variables in Settings
5. Deploy automatically triggers

### Step 3: Verify Deployment
Check deployment logs for:
```
✅ Model file OK: leaf-mobilenetv2.keras (9.26 MB)
✅ Model file OK: fruit-mobilenetv2.keras (9.22 MB)
✅ All model files are present and valid
163 static files copied to '/app/staticfiles'.
Starting Django Application
Server will bind to: 0.0.0.0:<PORT>
Running migrations...
Migrations complete
Starting Gunicorn...
[INFO] Listening at: http://0.0.0.0:<PORT>
```

### Step 4: Test API
```bash
# Health check
curl https://<your-railway-domain>.railway.app/health/

# API endpoint
curl https://<your-railway-domain>.railway.app/api/
```

---

## Common Issues & Solutions

### Issue 1: 502 Bad Gateway - Connection Timeout
**Cause**: Application not binding to correct port or not starting
**Solution**: 
- Ensure `$PORT` environment variable is used
- Check Railway logs for startup errors
- Verify start.sh is executable

### Issue 2: Model Files are 0 bytes
**Cause**: Git LFS pointers committed instead of actual files
**Solution**: Remove LFS tracking and commit actual files

### Issue 3: Static Files Not Found
**Cause**: Missing whitenoise or collectstatic not run
**Solution**: 
- Add whitenoise to requirements.txt and middleware
- Run collectstatic in Dockerfile build

### Issue 4: CORS Errors from Mobile App
**Cause**: CORS not configured for Capacitor/Ionic origins
**Solution**: Add capacitor:// and ionic:// to CORS_ALLOWED_ORIGINS

---

## Performance Considerations

### Memory Management
- **Model Loading**: TensorFlow models loaded once at startup
- **Worker Configuration**: Single worker prevents multiple model copies in memory
- **Thread Pool**: 4 threads handle concurrent requests efficiently

### Timeout Configuration
- **Gunicorn Timeout**: 300 seconds for ML inference
- **Railway Health Checks**: Configured for long startup time

### Request Handling
- **Image Upload**: Max size configured in Django settings
- **Prediction Pipeline**: Preprocessing → Model Inference → Response
- **Response Time**: ~2-5 seconds per prediction

---

## Monitoring & Maintenance

### Railway Logs
- Access logs via Railway dashboard
- Filter by error level
- Export logs for analysis

### Health Checks
- Endpoint: `/health/`
- Returns: JSON with service status and timestamp

### Model Updates
1. Update model files locally
2. Test locally with Docker
3. Commit and push to trigger deployment
4. Railway automatically rebuilds and redeploys

---

## File Structure
```
backend/
├── Dockerfile                 # Docker build configuration
├── start.sh                   # Startup script
├── railway.json               # Railway configuration
├── requirements.txt           # Python dependencies
├── check_models.py            # Model validation script
├── manage.py                  # Django management
├── mangoAPI/                  # Django project
│   ├── settings.py           # Production settings
│   ├── urls.py               # URL routing
│   └── wsgi.py               # WSGI application
├── mangosense/               # Django app
│   ├── models.py             # Database models
│   ├── views/                # API views
│   └── ML/                   # ML inference code
└── models/                   # TensorFlow models
    ├── leaf-mobilenetv2.keras
    └── fruit-mobilenetv2.keras
```

---

## Cost Optimization (Railway Free Tier)

### Resource Limits
- **Memory**: ~512 MB available
- **CPU**: Shared compute
- **Execution Time**: 500 hours/month

### Optimization Strategies
1. Single Gunicorn worker
2. Efficient model loading
3. Image preprocessing optimization
4. Lazy model initialization

---

## Deployment Checklist

- [x] Models committed directly (not LFS)
- [x] Dockerfile optimized for Railway
- [x] start.sh created and executable
- [x] Procfile and nixpacks.toml removed
- [x] railway.json configured with DOCKERFILE builder
- [x] CORS settings configured for mobile app
- [x] Whitenoise middleware added
- [x] Environment variables set in Railway
- [x] Health check endpoint working
- [x] API endpoints accessible
- [x] Model inference tested

---

## Conclusion

The deployment successfully runs a Django backend with TensorFlow ML models on Railway using Docker. Key success factors:

1. **Direct model storage** (no Git LFS)
2. **Single deployment configuration** (Dockerfile only)
3. **Proper startup script** (separate file with correct line endings)
4. **Optimized Gunicorn config** (single worker, multiple threads)
5. **Complete CORS setup** (mobile app compatibility)

The application now serves ML predictions at: `https://mangoapi.up.railway.app/api/`

---

**Last Updated**: October 27, 2025  
**Status**: ✅ Successfully Deployed
