from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from django.utils import timezone
import os

def health_check(request):
    """Simple health check that responds immediately during Railway deployment"""
    try:
        # Always return healthy for Railway health check
        # Full database checks can be done at /api/health/ endpoint
        return JsonResponse({
            "status": "healthy", 
            "message": "Django app is running",
            "service": "mangosense-backend",
            "port": os.environ.get('PORT', 'Not set'),
            "timestamp": timezone.now().isoformat(),
            "version": "1.0.0"
        }, status=200)
        
    except Exception as e:
        # Even if there's an error, return 200 for Railway health check
        return JsonResponse({
            "status": "starting",
            "message": "Service is initializing",
            "error": str(e),
            "timestamp": str(timezone.now()) if hasattr(timezone, 'now') else None
        }, status=200)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', health_check, name='health_check'),
    path('health/', health_check, name='health_check_alt'),
    path('api/', include('mangosense.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)