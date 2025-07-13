"""
Core views for JOTA News System.
"""
import logging
from django.http import JsonResponse
from django.db import connections
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import redis
import time

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Basic health check endpoint.
    """
    return JsonResponse({
        'status': 'healthy',
        'timestamp': time.time(),
        'version': '1.0.0',
        'service': 'jota-news-api'
    })


@csrf_exempt
@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness check - verifies all dependencies are available.
    """
    checks = {
        'database': check_database(),
        'redis': check_redis(),
        'elasticsearch': check_elasticsearch(),
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JsonResponse({
        'status': 'ready' if all_healthy else 'not_ready',
        'checks': checks,
        'timestamp': time.time(),
    }, status=status_code)


@csrf_exempt
@require_http_methods(["GET"])
def liveness_check(request):
    """
    Liveness check - verifies the application is running.
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': time.time(),
        'uptime': get_uptime(),
    })


def check_database():
    """Check database connectivity."""
    try:
        db_conn = connections['default']
        db_conn.cursor().execute('SELECT 1')
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def check_redis():
    """Check Redis connectivity."""
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


def check_elasticsearch():
    """Check Elasticsearch connectivity."""
    try:
        import requests
        response = requests.get(f"{settings.ELASTICSEARCH_URL}/_cluster/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Elasticsearch health check failed: {e}")
        return False


def get_uptime():
    """Get application uptime."""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            return uptime_seconds
    except:
        return 0


def dashboard_view(request):
    """Dashboard view."""
    return render(request, 'dashboard.html')


def handler404(request, exception):
    """Custom 404 handler."""
    return JsonResponse({
        'error': 'Not Found',
        'message': 'The requested resource was not found.',
        'status_code': 404,
        'path': request.path,
    }, status=404)


def handler500(request):
    """Custom 500 handler."""
    return JsonResponse({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred.',
        'status_code': 500,
        'path': request.path,
    }, status=500)