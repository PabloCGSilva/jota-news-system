"""
URL configuration for classification app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClassificationRuleViewSet, ClassificationModelViewSet,
    ClassificationResultViewSet, ClassificationTrainingDataViewSet,
    ClassificationStatisticViewSet, ClassificationAPIViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'rules', ClassificationRuleViewSet)
router.register(r'models', ClassificationModelViewSet)
router.register(r'results', ClassificationResultViewSet)
router.register(r'training-data', ClassificationTrainingDataViewSet)
router.register(r'statistics', ClassificationStatisticViewSet)
router.register(r'api', ClassificationAPIViewSet, basename='classification-api')

app_name = 'classification'

urlpatterns = [
    path('', include(router.urls)),
]