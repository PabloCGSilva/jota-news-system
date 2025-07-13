"""
Views for security monitoring and metrics.
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
def security_metrics(request):
    """Endpoint to expose security metrics in Prometheus format."""
    try:
        from .security_monitoring import get_security_metrics
        
        # Update metrics before serving
        metrics_data = get_security_metrics()
        
        # Return Prometheus format
        metrics_output = generate_latest()
        return HttpResponse(
            metrics_output,
            content_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Error generating security metrics: {e}")
        return HttpResponse(
            f"Error generating metrics: {str(e)}",
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def security_status(request):
    """Endpoint to get security status information."""
    try:
        from .security_monitoring import get_security_metrics
        
        # Get security metrics
        metrics_data = get_security_metrics()
        
        return HttpResponse(
            json.dumps(metrics_data, indent=2),
            content_type='application/json'
        )
    except Exception as e:
        logger.error(f"Error getting security status: {e}")
        return HttpResponse(
            json.dumps({'error': str(e)}),
            content_type='application/json',
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def security_health(request):
    """Health check endpoint for security monitoring."""
    try:
        from .security_monitoring import security_monitor
        from django.utils import timezone
        from datetime import timedelta
        
        # Check if security monitoring is working
        last_scan = security_monitor.last_security_scan
        is_recent = last_scan and (timezone.now() - last_scan) < timedelta(minutes=10)
        
        threat_level = security_monitor._calculate_threat_level()
        
        if is_recent and threat_level != 'unknown':
            return HttpResponse(
                json.dumps({
                    'status': 'healthy',
                    'threat_level': threat_level,
                    'last_scan': last_scan.isoformat(),
                    'blocked_ips': len(security_monitor.blocked_ips),
                    'scan_age_minutes': (timezone.now() - last_scan).total_seconds() / 60
                }),
                content_type='application/json'
            )
        else:
            return HttpResponse(
                json.dumps({
                    'status': 'degraded',
                    'threat_level': threat_level,
                    'last_scan': last_scan.isoformat() if last_scan else None,
                    'error': 'Security monitoring is not up to date'
                }),
                content_type='application/json',
                status=503
            )
    except Exception as e:
        logger.error(f"Error checking security health: {e}")
        return HttpResponse(
            json.dumps({
                'status': 'error',
                'error': str(e)
            }),
            content_type='application/json',
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def security_incidents(request):
    """Endpoint to get recent security incidents."""
    try:
        from .security_monitoring import security_monitor
        
        # Get recent security events
        recent_events = security_monitor._get_recent_security_events()
        
        return HttpResponse(
            json.dumps({
                'incidents': recent_events,
                'total_count': len(recent_events),
                'threat_level': security_monitor._calculate_threat_level(),
                'blocked_ips': len(security_monitor.blocked_ips)
            }, indent=2),
            content_type='application/json'
        )
    except Exception as e:
        logger.error(f"Error getting security incidents: {e}")
        return HttpResponse(
            json.dumps({'error': str(e)}),
            content_type='application/json',
            status=500
        )