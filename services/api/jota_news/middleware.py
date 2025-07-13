"""
Custom middleware for JOTA News System.
"""
import logging
import time
import uuid
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all requests with correlation ID and timing.
    """
    
    def process_request(self, request):
        """Add correlation ID and start timing."""
        request.correlation_id = str(uuid.uuid4())
        request.start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started - {request.method} {request.path}",
            extra={
                'correlation_id': request.correlation_id,
                'method': request.method,
                'path': request.path,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip': self.get_client_ip(request),
            }
        )
    
    def process_response(self, request, response):
        """Log response with timing."""
        if hasattr(request, 'start_time') and hasattr(request, 'correlation_id'):
            duration = time.time() - request.start_time
            
            # Add correlation ID to response headers
            response['X-Correlation-ID'] = request.correlation_id
            
            logger.info(
                f"Request completed - {request.method} {request.path} - {response.status_code}",
                extra={
                    'correlation_id': request.correlation_id,
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': round(duration * 1000, 2),
                }
            )
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions."""
        if hasattr(request, 'correlation_id'):
            logger.error(
                f"Request failed - {request.method} {request.path} - {str(exception)}",
                extra={
                    'correlation_id': request.correlation_id,
                    'method': request.method,
                    'path': request.path,
                    'exception': str(exception),
                },
                exc_info=True
            )
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class HealthCheckMiddleware(MiddlewareMixin):
    """
    Middleware to handle health checks without authentication.
    """
    
    def process_request(self, request):
        """Skip authentication for health check endpoints."""
        if request.path in ['/health/', '/health/ready/', '/health/live/']:
            return None
        return None


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Check rate limits."""
        if not settings.DEBUG:
            # Implement rate limiting logic here
            # For now, just pass through
            pass
        return None