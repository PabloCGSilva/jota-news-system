"""
URL configuration for jota_news project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from . import api_docs
from . import views
from . import celery_views
from . import business_views
from . import security_views

# API URL patterns
api_v1_patterns = [
    path('auth/', include('apps.authentication.urls')),
    path('news/', include('apps.news.urls')),
    path('webhooks/', include('apps.webhooks.urls')),
    path('classification/', include('apps.classification.urls')),
    path('notifications/', include('apps.notifications.urls')),
]

urlpatterns = [
    # Main Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # Demo Interface
    path('demo/', include('apps.demo.urls')),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API Overview
    path('api/', api_docs.api_overview, name='api_overview'),
    
    # API v1 Root
    path('api/v1/', api_docs.api_v1_root, name='api_v1_root'),
    
    # API v1 Sub-endpoints
    path('api/v1/', include(api_v1_patterns)),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Health Check
    path('health/', include('jota_news.health_urls')),
    
    # Metrics (Prometheus)
    path('', include('django_prometheus.urls')),
    
    # Celery Monitoring
    path('celery/metrics/', celery_views.celery_metrics, name='celery_metrics'),
    path('celery/status/', celery_views.celery_status, name='celery_status'),
    path('celery/health/', celery_views.celery_health, name='celery_health'),
    
    # Business Metrics
    path('business/metrics/', business_views.business_metrics, name='business_metrics'),
    path('business/status/', business_views.business_status, name='business_status'),
    path('business/health/', business_views.business_health, name='business_health'),
    
    # Security Monitoring
    path('security/metrics/', security_views.security_metrics, name='security_metrics'),
    path('security/status/', security_views.security_status, name='security_status'),
    path('security/health/', security_views.security_health, name='security_health'),
    path('security/incidents/', security_views.security_incidents, name='security_incidents'),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler404 = 'jota_news.views.handler404'
handler500 = 'jota_news.views.handler500'