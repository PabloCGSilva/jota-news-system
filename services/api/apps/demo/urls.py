"""
URL configuration for demo app.
"""
from django.urls import path
from . import views

app_name = 'demo'

urlpatterns = [
    path('', views.demo_dashboard, name='dashboard'),
    path('action/', views.run_demo_action, name='run_action'),
    path('api/status/', views.system_status_api, name='system_status'),
]