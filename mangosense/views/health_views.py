from django.http import JsonResponse
from django.db import connection
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for Railway deployment
    Returns 200 OK if service is healthy, 503 if unhealthy
    
    Checks:
    - Database connectivity
    - Basic model imports
    - Application responsiveness
    """
    try:
        # Check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        # Check if models can be imported (basic app health)
        from ..models import MangoImage
        
        # Get basic statistics for health verification
        try:
            image_count = MangoImage.objects.count()
        except Exception:
            image_count = 0
        
        return JsonResponse({
            'status': 'healthy',
            'service': 'mangosense-backend',
            'database': 'connected',
            'models': 'accessible',
            'image_count': image_count,
            'timestamp': timezone.now().isoformat(),
            'version': '1.0.0'
        }, status=200)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'service': 'mangosense-backend',
            'timestamp': timezone.now().isoformat()
        }, status=503)