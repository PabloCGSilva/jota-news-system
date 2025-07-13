"""
Enhanced API documentation views and utilities.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes


@extend_schema(
    summary="API Overview",
    description="""
    JOTA News System API provides comprehensive endpoints for managing news articles,
    webhooks, classification, and notifications.
    
    ## Quick Start
    
    1. **Authentication**: Obtain a JWT token by posting to `/api/v1/auth/token/`
    2. **Explore**: Use the interactive documentation at `/api/docs/`
    3. **Test**: Try endpoints using the built-in testing interface
    
    ## Core Endpoints
    
    - **News**: `/api/v1/news/` - Manage news articles, categories, and tags
    - **Webhooks**: `/api/v1/webhooks/` - Configure and monitor webhook sources
    - **Classification**: `/api/v1/classification/` - AI-powered news classification
    - **Notifications**: `/api/v1/notifications/` - Multi-channel notification system
    
    ## Rate Limits
    
    - Authenticated: 1000 requests/hour
    - Anonymous: 100 requests/hour
    - Webhooks: Configurable per source
    
    ## Examples
    
    ### Create News Article
    ```
    POST /api/v1/news/articles/
    Authorization: Bearer <your_token>
    Content-Type: application/json
    
    {
      "title": "Breaking News",
      "content": "Article content...",
      "category": "category_id",
      "tags": ["tag1", "tag2"],
      "is_urgent": false
    }
    ```
    
    ### Send Webhook
    ```
    POST /api/v1/webhooks/receive/source-name/
    Content-Type: application/json
    X-Hub-Signature-256: sha256=signature
    
    {
      "title": "External News",
      "content": "Content from external source...",
      "source": "External API"
    }
    ```
    """,
    responses={
        200: {
            'description': 'API overview information',
            'example': {
                'version': '1.0.0',
                'title': 'JOTA News System API',
                'endpoints': {
                    'news': '/api/v1/news/',
                    'webhooks': '/api/v1/webhooks/',
                    'classification': '/api/v1/classification/',
                    'notifications': '/api/v1/notifications/'
                }
            }
        }
    },
    tags=['API Overview']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def api_overview(request):
    """
    Get API overview and basic information.
    """
    return Response({
        'version': '1.0.0',
        'title': 'JOTA News System API',
        'description': 'A comprehensive news processing and notification system',
        'endpoints': {
            'news': '/api/v1/news/',
            'webhooks': '/api/v1/webhooks/',
            'classification': '/api/v1/classification/',
            'notifications': '/api/v1/notifications/',
            'auth': '/api/v1/auth/',
            'docs': '/api/docs/',
            'schema': '/api/schema/'
        },
        'documentation': {
            'swagger': request.build_absolute_uri('/api/docs/'),
            'redoc': request.build_absolute_uri('/api/redoc/'),
            'openapi': request.build_absolute_uri('/api/schema/')
        },
        'features': [
            'News Management with Categories and Tags',
            'Webhook Integration with Signature Verification',
            'AI-Powered News Classification',
            'Multi-Channel Notifications (WhatsApp, Email, Slack, SMS)',
            'User Subscription Management',
            'Real-time Monitoring and Analytics',
            'Comprehensive API Documentation',
            'Rate Limiting and Security'
        ],
        'authentication': {
            'type': 'JWT Bearer Token',
            'token_endpoint': '/api/v1/auth/token/',
            'refresh_endpoint': '/api/v1/auth/token/refresh/',
            'header_format': 'Authorization: Bearer <token>'
        },
        'rate_limits': {
            'authenticated_users': '1000 requests/hour',
            'anonymous_users': '100 requests/hour',
            'webhook_endpoints': 'Configurable per source'
        },
        'support': {
            'email': 'dev@jota.news',
            'documentation': 'https://docs.jota.news',
            'github': 'https://github.com/jota/news-system'
        }
    })


@extend_schema(
    summary="API Health Check",
    description="Check the health status of the API and its dependencies.",
    responses={
        200: {
            'description': 'API is healthy',
            'example': {
                'status': 'healthy',
                'timestamp': '2024-01-15T10:30:00Z',
                'version': '1.0.0',
                'services': {
                    'database': 'healthy',
                    'redis': 'healthy'
                }
            }
        },
        503: {
            'description': 'API is unhealthy',
            'example': {
                'status': 'unhealthy',
                'timestamp': '2024-01-15T10:30:00Z',
                'version': '1.0.0',
                'services': {
                    'database': 'healthy',
                    'redis': 'unhealthy'
                }
            }
        }
    },
    tags=['Monitoring']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Comprehensive health check for the API and its dependencies.
    """
    from django.db import connection
    from django.core.cache import cache
    from django.utils import timezone
    import redis
    
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0',
        'services': {}
    }
    
    overall_healthy = True
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['services']['database'] = 'healthy'
    except Exception as e:
        health_status['services']['database'] = f'unhealthy: {str(e)}'
        overall_healthy = False
    
    # Check Redis/Cache
    try:
        cache.set('health_check', 'test', 10)
        if cache.get('health_check') == 'test':
            health_status['services']['redis'] = 'healthy'
        else:
            health_status['services']['redis'] = 'unhealthy: cache test failed'
            overall_healthy = False
    except Exception as e:
        health_status['services']['redis'] = f'unhealthy: {str(e)}'
        overall_healthy = False
    
    
    # Check Celery workers (basic check)
    try:
        from celery import current_app
        stats = current_app.control.stats()
        if stats:
            health_status['services']['celery'] = 'healthy'
        else:
            health_status['services']['celery'] = 'degraded: no workers responding'
            # Don't mark as unhealthy since it might be acceptable
    except Exception as e:
        health_status['services']['celery'] = f'unhealthy: {str(e)}'
        overall_healthy = False
    
    if not overall_healthy:
        health_status['status'] = 'unhealthy'
        return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    return Response(health_status)


@extend_schema(
    summary="API Statistics",
    description="Get general statistics about the API usage and system metrics.",
    responses={
        200: {
            'description': 'API statistics',
            'example': {
                'news': {
                    'total_articles': 1250,
                    'categories': 5,
                    'tags': 120,
                    'urgent_today': 3
                },
                'webhooks': {
                    'total_sources': 8,
                    'active_sources': 6,
                    'requests_today': 450,
                    'success_rate': 98.5
                },
                'notifications': {
                    'total_sent_today': 125,
                    'channels': 4,
                    'delivery_rate': 96.2
                }
            }
        }
    },
    tags=['Monitoring']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def api_statistics(request):
    """
    Get general API statistics and usage metrics.
    """
    from apps.news.models import News, Category, Tag
    from apps.webhooks.models import WebhookSource, WebhookLog
    from apps.notifications.models import NotificationChannel, NotificationLog
    from django.utils import timezone
    from django.db.models import Count, Q
    
    today = timezone.now().date()
    
    # News statistics
    news_stats = {
        'total_articles': News.objects.count(),
        'categories': Category.objects.filter(is_active=True).count(),
        'tags': Tag.objects.count(),
        'urgent_today': News.objects.filter(
            is_urgent=True,
            created_at__date=today
        ).count(),
        'published_today': News.objects.filter(
            created_at__date=today
        ).count()
    }
    
    # Webhook statistics
    webhook_logs_today = WebhookLog.objects.filter(created_at__date=today)
    total_webhooks_today = webhook_logs_today.count()
    successful_webhooks_today = webhook_logs_today.filter(status='success').count()
    
    webhook_stats = {
        'total_sources': WebhookSource.objects.count(),
        'active_sources': WebhookSource.objects.filter(is_active=True).count(),
        'requests_today': total_webhooks_today,
        'success_rate': round(
            (successful_webhooks_today / total_webhooks_today * 100) if total_webhooks_today > 0 else 0,
            2
        )
    }
    
    # Notification statistics
    notification_logs_today = NotificationLog.objects.filter(created_at__date=today)
    total_notifications_today = notification_logs_today.count()
    delivered_notifications_today = notification_logs_today.filter(status='delivered').count()
    
    notification_stats = {
        'total_sent_today': total_notifications_today,
        'channels': NotificationChannel.objects.filter(is_active=True).count(),
        'delivery_rate': round(
            (delivered_notifications_today / total_notifications_today * 100) if total_notifications_today > 0 else 0,
            2
        )
    }
    
    return Response({
        'date': today.isoformat(),
        'news': news_stats,
        'webhooks': webhook_stats,
        'notifications': notification_stats,
        'system': {
            'uptime': 'Available via /health/',
            'version': '1.0.0'
        }
    })


@extend_schema(
    summary="API v1 Root",
    description="Root endpoint for API v1 with available endpoints and quick navigation.",
    responses={
        200: {
            'description': 'API v1 root information',
            'example': {
                'version': '1.0.0',
                'title': 'JOTA News System API v1',
                'endpoints': {
                    'auth': '/api/v1/auth/',
                    'news': '/api/v1/news/',
                    'webhooks': '/api/v1/webhooks/',
                    'classification': '/api/v1/classification/',
                    'notifications': '/api/v1/notifications/'
                }
            }
        }
    },
    tags=['API Root']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def api_v1_root(request):
    """
    API v1 root endpoint with navigation to all available endpoints.
    """
    return Response({
        'version': '1.0.0',
        'title': 'JOTA News System API v1',
        'description': 'REST API for the JOTA News Processing System',
        'endpoints': {
            'auth': {
                'url': '/api/v1/auth/',
                'description': 'Authentication and user management'
            },
            'news': {
                'url': '/api/v1/news/',
                'description': 'News articles, categories, and tags'
            },
            'webhooks': {
                'url': '/api/v1/webhooks/',
                'description': 'Webhook sources and processing'
            },
            'classification': {
                'url': '/api/v1/classification/',
                'description': 'AI-powered news classification'
            },
            'notifications': {
                'url': '/api/v1/notifications/',
                'description': 'Multi-channel notification system'
            }
        },
        'documentation': {
            'swagger': request.build_absolute_uri('/api/docs/'),
            'redoc': request.build_absolute_uri('/api/redoc/'),
            'openapi': request.build_absolute_uri('/api/schema/')
        },
        'authentication': {
            'type': 'JWT Bearer Token',
            'token_endpoint': '/api/v1/auth/token/',
            'refresh_endpoint': '/api/v1/auth/token/refresh/'
        }
    })