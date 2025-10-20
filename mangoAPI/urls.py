from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from django.utils import timezone
import os

def health_check(request):
    try:
        from django.db import connection
        from django.utils import timezone
        
        # Check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        # Check if basic models can be imported
        try:
            from mangosense.models import MangoImage
            image_count = MangoImage.objects.count()
        except Exception:
            image_count = 0
            
        return JsonResponse({
            "status": "healthy", 
            "message": "Django app is running and database is connected",
            "database": "connected",
            "image_count": image_count,
            "port": os.environ.get('PORT', 'Not set'),
            "timestamp": timezone.now().isoformat(),
            "version": "1.0.0"
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            "status": "unhealthy",
            "error": str(e),
            "message": "Service is starting up or database not ready",
            "timestamp": timezone.now().isoformat() if 'timezone' in locals() else None
        }, status=503)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', health_check, name='health_check'),
    path('health/', health_check, name='health_check_alt'),
    path('api/', include('mangosense.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)