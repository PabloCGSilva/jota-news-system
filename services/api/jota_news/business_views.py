"""
Views for business metrics and monitoring.
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
def business_metrics(request):
    """Endpoint to expose business metrics in Prometheus format."""
    try:
        from .business_metrics import get_business_metrics
        
        # Update metrics before serving
        metrics_data = get_business_metrics()
        
        # Return Prometheus format
        metrics_output = generate_latest()
        return HttpResponse(
            metrics_output,
            content_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Error generating business metrics: {e}")
        return HttpResponse(
            f"Error generating metrics: {str(e)}",
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def business_status(request):
    """Endpoint to get business status information."""
    try:
        from .business_metrics import get_business_metrics
        
        # Get business metrics
        metrics_data = get_business_metrics()
        
        return HttpResponse(
            json.dumps(metrics_data, indent=2),
            content_type='application/json'
        )
    except Exception as e:
        logger.error(f"Error getting business status: {e}")
        return HttpResponse(
            json.dumps({'error': str(e)}),
            content_type='application/json',
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def business_health(request):
    """Health check endpoint for business metrics."""
    try:
        from .business_metrics import business_metrics_collector
        from django.utils import timezone
        from datetime import timedelta
        
        # Check if metrics are recent
        last_update = business_metrics_collector.last_update
        is_recent = last_update and (timezone.now() - last_update) < timedelta(minutes=5)
        
        if is_recent:
            return HttpResponse(
                json.dumps({
                    'status': 'healthy',
                    'last_update': last_update.isoformat(),
                    'metrics_age_minutes': (timezone.now() - last_update).total_seconds() / 60
                }),
                content_type='application/json'
            )
        else:
            return HttpResponse(
                json.dumps({
                    'status': 'stale',
                    'last_update': last_update.isoformat() if last_update else None,
                    'error': 'Metrics are stale or not initialized'
                }),
                content_type='application/json',
                status=503
            )
    except Exception as e:
        logger.error(f"Error checking business health: {e}")
        return HttpResponse(
            json.dumps({
                'status': 'error',
                'error': str(e)
            }),
            content_type='application/json',
            status=500
        )