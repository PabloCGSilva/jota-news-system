"""
URL configuration for news app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, SubcategoryViewSet, TagViewSet, NewsViewSet,
    NewsProcessingLogViewSet, NewsStatisticViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubcategoryViewSet)
router.register(r'tags', TagViewSet)
router.register(r'articles', NewsViewSet)
router.register(r'processing-logs', NewsProcessingLogViewSet)
router.register(r'statistics', NewsStatisticViewSet)

app_name = 'news'

urlpatterns = [
    path('', include(router.urls)),
]