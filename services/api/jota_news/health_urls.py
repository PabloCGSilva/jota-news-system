"""
Health check URLs for monitoring.
"""
from django.urls import path
from . import views, api_docs

urlpatterns = [
    path('', views.health_check, name='health_check'),
    path('ready/', views.readiness_check, name='readiness_check'),
    path('live/', views.liveness_check, name='liveness_check'),
    path('stats/', api_docs.api_statistics, name='api_statistics'),
]