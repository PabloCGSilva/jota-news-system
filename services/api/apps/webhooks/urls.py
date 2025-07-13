"""
URL configuration for webhook app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WebhookSourceViewSet, WebhookLogViewSet, WebhookStatisticViewSet,
    news_webhook, webhook_dashboard
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'sources', WebhookSourceViewSet)
router.register(r'logs', WebhookLogViewSet)
router.register(r'statistics', WebhookStatisticViewSet)

app_name = 'webhooks'

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    
    # Dashboard
    path('dashboard/', webhook_dashboard, name='dashboard'),
    
    # Webhook receivers
    path('receive/<str:source_name>/', news_webhook, name='news_webhook'),
]