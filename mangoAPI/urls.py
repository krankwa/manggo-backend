from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from django.utils import timezone

def health_check(request):
    """Simple health check for Render deployment"""
    return JsonResponse({
        "status": "healthy",
        "service": "mangosense-backend",
        "timestamp": timezone.now().isoformat()
    }, status=200)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', health_check, name='health_check'),
    path('health/', health_check, name='health_check_alt'),
    path('api/', include('mangosense.urls')),
]

