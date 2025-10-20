from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.conf.urls.static import static
import os
import datetime

def health_check(request):
    """Ultra simple health check for Railway deployment"""
    try:
        return JsonResponse({
            "status": "healthy",
            "service": "mangosense-backend",
            "timestamp": datetime.datetime.now().isoformat()
        }, status=200)
    except:
        # If JSON fails, return plain text
        return HttpResponse("OK", status=200)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', health_check, name='health_check'),
    path('health/', health_check, name='health_check_alt'),
    path('api/', include('mangosense.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)