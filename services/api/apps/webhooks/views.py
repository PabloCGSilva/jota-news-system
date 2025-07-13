"""
Views for webhook app.
"""
import json
import hashlib
import hmac
import time
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.conf import settings
from django.utils import timezone
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes

from .models import WebhookSource, WebhookLog, WebhookRetry, WebhookStatistic
from .serializers import (
    WebhookSourceSerializer, WebhookLogSerializer, WebhookRetrySerializer,
    WebhookStatisticSerializer, NewsWebhookSerializer,
    WebhookTestSerializer
)
from .utils import get_client_ip, verify_webhook_signature, rate_limit_check
from .tasks import process_webhook_async, update_webhook_statistics

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="List webhook sources",
        description="Get a list of all webhook sources and their configurations."
    ),
    create=extend_schema(
        summary="Create webhook source",
        description="Create a new webhook source configuration."
    ),
    retrieve=extend_schema(
        summary="Get webhook source details",
        description="Get detailed information about a specific webhook source."
    ),
    update=extend_schema(
        summary="Update webhook source",
        description="Update an existing webhook source configuration."
    ),
)
class WebhookSourceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing webhook sources.
    """
    queryset = WebhookSource.objects.all()
    serializer_class = WebhookSourceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'requires_authentication']
    
    @extend_schema(
        summary="Get webhook source statistics",
        description="Get detailed statistics for a webhook source."
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get webhook source statistics."""
        source = self.get_object()
        
        # Get recent statistics
        recent_stats = WebhookStatistic.objects.filter(
            source=source,
            date__gte=timezone.now().date() - timezone.timedelta(days=30)
        ).order_by('-date')
        
        serializer = WebhookStatisticSerializer(recent_stats, many=True)
        
        return Response({
            'source': WebhookSourceSerializer(source).data,
            'recent_statistics': serializer.data
        })
    
    @extend_schema(
        summary="Test webhook source",
        description="Test a webhook source with sample data."
    )
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test webhook source."""
        source = self.get_object()
        
        # Sample test data
        test_data = {
            'title': 'Test News Article',
            'content': 'This is a test news article content to verify webhook functionality.',
            'source': 'Test Source',
            'author': 'Test Author',
            'is_urgent': False
        }
        
        # Create webhook log
        webhook_log = WebhookLog.objects.create(
            source=source,
            method='POST',
            path=f'/test/{source.id}/',
            headers={'Content-Type': 'application/json'},
            body=json.dumps(test_data),
            remote_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            correlation_id=f'test-{int(time.time())}'
        )
        
        # Process webhook asynchronously
        process_webhook_async.delay(webhook_log.id)
        
        return Response({
            'message': 'Test webhook submitted for processing',
            'webhook_log_id': webhook_log.id
        })


@extend_schema_view(
    list=extend_schema(
        summary="List webhook logs",
        description="Get a list of webhook request logs with filtering options."
    ),
    retrieve=extend_schema(
        summary="Get webhook log details",
        description="Get detailed information about a specific webhook log."
    ),
)
class WebhookLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing webhook logs.
    """
    queryset = WebhookLog.objects.all()
    serializer_class = WebhookLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['source', 'status', 'method']
    ordering = ['-created_at']
    
    @extend_schema(
        summary="Retry webhook processing",
        description="Retry processing for a failed webhook."
    )
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry webhook processing."""
        webhook_log = self.get_object()
        
        if webhook_log.status != 'failed':
            return Response(
                {'error': 'Only failed webhooks can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset status to pending
        webhook_log.status = 'pending'
        webhook_log.save()
        
        # Create retry record
        retry_count = webhook_log.retries.count()
        WebhookRetry.objects.create(
            webhook_log=webhook_log,
            attempt_number=retry_count + 1,
            error_message=webhook_log.error_message,
            next_retry_at=timezone.now()
        )
        
        # Process webhook asynchronously
        process_webhook_async.delay(webhook_log.id)
        
        return Response({'message': 'Webhook retry initiated'})


@extend_schema_view(
    list=extend_schema(
        summary="List webhook statistics",
        description="Get webhook statistics by date and source."
    ),
)
class WebhookStatisticViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing webhook statistics.
    """
    queryset = WebhookStatistic.objects.all()
    serializer_class = WebhookStatisticSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['source', 'date']
    ordering = ['-date']


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@extend_schema(
    summary="Generic news webhook receiver",
    description="Generic endpoint to receive news from external sources.",
    request=NewsWebhookSerializer,
    responses={
        200: {'description': 'Webhook processed successfully'},
        400: {'description': 'Invalid webhook data'},
        429: {'description': 'Rate limit exceeded'},
        500: {'description': 'Internal server error'}
    }
)
def news_webhook(request, source_name):
    """
    Generic webhook receiver for news.
    """
    start_time = time.time()
    
    try:
        # Get webhook source
        try:
            source = WebhookSource.objects.get(name=source_name, is_active=True)
        except WebhookSource.DoesNotExist:
            return JsonResponse(
                {'error': 'Webhook source not found or inactive'},
                status=404
            )
        
        # Rate limiting check
        if not rate_limit_check(source, get_client_ip(request)):
            return JsonResponse(
                {'error': 'Rate limit exceeded'},
                status=429
            )
        
        # Verify content type
        content_type = request.content_type
        if content_type != source.expected_content_type:
            return JsonResponse(
                {'error': f'Expected content type {source.expected_content_type}'},
                status=400
            )
        
        # Verify webhook signature if required
        if source.requires_authentication:
            if not verify_webhook_signature(request, source.secret_key):
                return JsonResponse(
                    {'error': 'Invalid webhook signature'},
                    status=401
                )
        
        # Parse request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'Invalid JSON data'},
                status=400
            )
        
        # Create webhook log
        webhook_log = WebhookLog.objects.create(
            source=source,
            method=request.method,
            path=request.path,
            headers=dict(request.headers),
            query_params=dict(request.GET),
            body=request.body.decode('utf-8'),
            remote_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            correlation_id=request.headers.get('X-Correlation-ID', ''),
            status='processing'
        )
        
        # Update source statistics
        source.increment_total_requests()
        
        # Process webhook asynchronously
        process_webhook_async.delay(webhook_log.id)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        webhook_log.processing_time = processing_time
        webhook_log.save()
        
        return JsonResponse({
            'message': 'Webhook received and queued for processing',
            'webhook_log_id': str(webhook_log.id),
            'processing_time': processing_time
        })
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'Internal server error'},
            status=500
        )


@csrf_exempt
# WhatsApp webhook endpoint removed - external META Business API dependency not needed


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@extend_schema(
    summary="Get webhook dashboard data",
    description="Get aggregated webhook statistics for dashboard display."
)
def webhook_dashboard(request):
    """
    Get webhook dashboard data.
    """
    # Get recent statistics
    today = timezone.now().date()
    week_ago = today - timezone.timedelta(days=7)
    
    # Overall statistics
    total_sources = WebhookSource.objects.filter(is_active=True).count()
    total_logs = WebhookLog.objects.filter(created_at__date__gte=week_ago).count()
    success_rate = WebhookLog.objects.filter(
        created_at__date__gte=week_ago,
        status='success'
    ).count() / max(total_logs, 1) * 100
    
    # Recent activity
    recent_logs = WebhookLog.objects.filter(
        created_at__date__gte=week_ago
    ).order_by('-created_at')[:10]
    
    # Source statistics
    source_stats = []
    for source in WebhookSource.objects.filter(is_active=True):
        stats = WebhookStatistic.objects.filter(
            source=source,
            date__gte=week_ago
        ).aggregate(
            total_requests=models.Sum('total_requests'),
            successful_requests=models.Sum('successful_requests'),
            failed_requests=models.Sum('failed_requests')
        )
        
        source_stats.append({
            'source': WebhookSourceSerializer(source).data,
            'stats': stats
        })
    
    return Response({
        'overview': {
            'total_sources': total_sources,
            'total_logs': total_logs,
            'success_rate': round(success_rate, 2)
        },
        'recent_logs': WebhookLogSerializer(recent_logs, many=True).data,
        'source_statistics': source_stats
    })