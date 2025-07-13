"""
URL configuration for notifications app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationChannelViewSet, NotificationSubscriptionViewSet,
    NotificationTemplateViewSet, NotificationViewSet,
    NotificationStatisticViewSet, NotificationAPIViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'channels', NotificationChannelViewSet)
router.register(r'subscriptions', NotificationSubscriptionViewSet, basename='subscription')
router.register(r'templates', NotificationTemplateViewSet)
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'statistics', NotificationStatisticViewSet)
router.register(r'api', NotificationAPIViewSet, basename='notification-api')

app_name = 'notifications'

urlpatterns = [
    path('', include(router.urls)),
]