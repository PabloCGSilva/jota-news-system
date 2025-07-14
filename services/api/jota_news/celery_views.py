"""
Views for Celery monitoring and metrics.
"""
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import json
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@csrf_exempt
def celery_metrics(request):
    """Endpoint to expose Celery metrics in Prometheus format."""
    try:
        from .celery_monitoring import get_celery_metrics
        
        # Update metrics before serving
        metrics_data = get_celery_metrics()
        
        # Return Prometheus format
        metrics_output = generate_latest()
        return HttpResponse(
            metrics_output,
            content_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Error generating Celery metrics: {e}")
        return HttpResponse(
            f"Error generating metrics: {str(e)}",
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def celery_status(request):
    """Endpoint to get Celery status information."""
    try:
        from celery import current_app
        from .celery_monitoring import celery_monitor
        
        # Get basic Celery information
        inspect = current_app.control.inspect()
        
        status_data = {
            'active_workers': celery_monitor.worker_count,
            'active_tasks': len(celery_monitor.active_tasks),
            'registered_tasks': list(current_app.tasks.keys()),
            'worker_stats': inspect.stats() if inspect else {},
            'active_queues': inspect.active_queues() if inspect else {},
        }
        
        return HttpResponse(
            json.dumps(status_data, indent=2),
            content_type='application/json'
        )
    except Exception as e:
        logger.error(f"Error getting Celery status: {e}")
        return HttpResponse(
            json.dumps({'error': str(e)}),
            content_type='application/json',
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def celery_health(request):
    """Health check endpoint for Celery workers."""
    try:
        from celery import current_app
        from django.utils import timezone
        
        # Check if we can connect to Celery with timeout
        inspect = current_app.control.inspect(timeout=2.0)  # 2 second timeout
        
        # Try multiple methods to detect workers
        stats = None
        ping_result = None
        
        try:
            stats = inspect.stats()
        except Exception as e:
            logger.warning(f"Failed to get stats: {e}")
        
        try:
            ping_result = inspect.ping()
        except Exception as e:
            logger.warning(f"Failed to ping workers: {e}")
        
        # Consider workers available if either method succeeds
        if stats or ping_result:
            worker_count = len(stats) if stats else len(ping_result) if ping_result else 0
            return HttpResponse(
                json.dumps({
                    'status': 'healthy',
                    'workers': worker_count,
                    'timestamp': str(timezone.now()),
                    'detection_method': 'stats' if stats else 'ping'
                }),
                content_type='application/json'
            )
        else:
            return HttpResponse(
                json.dumps({
                    'status': 'unhealthy',
                    'error': 'No workers available or workers not responding',
                    'timestamp': str(timezone.now())
                }),
                content_type='application/json',
                status=503
            )
    except Exception as e:
        logger.error(f"Error checking Celery health: {e}")
        return HttpResponse(
            json.dumps({
                'status': 'error',
                'error': str(e),
                'timestamp': str(timezone.now()) if 'timezone' in globals() else 'unknown'
            }),
            content_type='application/json',
            status=500
        )