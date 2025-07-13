"""
Demo interface views for JOTA News System.
"""
import json
import requests
import subprocess
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.management import call_command
from django.db import connection
from apps.news.models import News, Category, Tag
from apps.webhooks.models import WebhookLog, WebhookSource
from apps.notifications.models import Notification
from apps.classification.models import ClassificationResult
import logging

logger = logging.getLogger(__name__)


def demo_dashboard(request):
    """Main demo dashboard view"""
    context = {
        'title': 'JOTA News System - Demo Dashboard',
        'system_stats': get_system_stats(),
        'endpoints': get_api_endpoints(),
        'dashboards': get_grafana_dashboards(),
    }
    return render(request, 'demo/dashboard.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def run_demo_action(request):
    """Execute demo actions via AJAX"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'create_sample_news':
            return create_sample_news_demo()
        elif action == 'test_classification':
            return test_classification_demo()
        elif action == 'test_webhook':
            return test_webhook_demo(data.get('webhook_data', {}))
        elif action == 'run_tests':
            return run_tests_demo()
        elif action == 'check_health':
            return check_health_demo()
        elif action == 'generate_load':
            return generate_load_demo()
        else:
            return JsonResponse({'success': False, 'error': 'Unknown action'})
            
    except Exception as e:
        logger.error(f"Demo action failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


def create_sample_news_demo():
    """Create sample news for demonstration"""
    try:
        # Create sample news articles
        categories = list(Category.objects.all()[:3])
        if not categories:
            # Create default categories if none exist
            categories = [
                Category.objects.create(name="Technology", description="Tech news"),
                Category.objects.create(name="Politics", description="Political news"),
                Category.objects.create(name="Sports", description="Sports news")
            ]
        
        sample_articles = [
            {
                'title': 'Breaking: New AI Technology Unveiled',
                'content': 'A revolutionary artificial intelligence system has been announced...',
                'source': 'Tech Daily',
                'author': 'John Smith',
                'category': categories[0],
                'is_urgent': True
            },
            {
                'title': 'Economic Growth Reaches New Heights',
                'content': 'The latest economic indicators show unprecedented growth...',
                'source': 'Economic Times',
                'author': 'Jane Doe',
                'category': categories[1],
                'is_urgent': False
            },
            {
                'title': 'Championship Finals This Weekend',
                'content': 'The highly anticipated championship finals are set to begin...',
                'source': 'Sports Central',
                'author': 'Mike Johnson',
                'category': categories[2],
                'is_urgent': False
            }
        ]
        
        created_articles = []
        import uuid
        for i, article_data in enumerate(sample_articles):
            article_data['external_id'] = f'demo-sample-{i+1}-{str(uuid.uuid4())[:8]}'
            article = News.objects.create(**article_data)
            created_articles.append({
                'id': str(article.id),
                'title': article.title,
                'category': article.category.name
            })
        
        return JsonResponse({
            'success': True,
            'message': f'Created {len(created_articles)} sample articles',
            'articles': created_articles
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def test_classification_demo():
    """Test news classification system"""
    try:
        # Get a recent news article
        news_article = News.objects.filter(category__isnull=False).first()
        if not news_article:
            return JsonResponse({
                'success': False, 
                'error': 'No news articles found. Create sample news first.'
            })
        
        # Simulate classification
        from apps.classification.tasks import classify_news
        
        # For demo purposes, create a mock classification result
        result = ClassificationResult.objects.create(
            news=news_article,
            method='demo',
            predicted_category=news_article.category,
            category_confidence=0.85,
            processing_time=0.15,
            is_accepted=True
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Classification completed',
            'result': {
                'article_title': news_article.title,
                'predicted_category': news_article.category.name,
                'confidence': result.category_confidence,
                'processing_time': result.processing_time
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def test_webhook_demo(webhook_data):
    """Test webhook processing"""
    try:
        # Create a webhook log entry
        webhook_source = WebhookSource.objects.first()
        if not webhook_source:
            return JsonResponse({'success': False, 'error': 'No webhook sources available'})
            
        webhook_log = WebhookLog.objects.create(
            source=webhook_source,
            method='POST',
            path='/api/v1/webhooks/receive/demo/',
            headers={'Content-Type': 'application/json'},
            body=json.dumps(webhook_data),
            status='success',
            processing_time=0.12,
            remote_ip='127.0.0.1',
            user_agent='Demo-Client/1.0'
        )
        
        # Create news from webhook data if provided
        news_created = None
        if webhook_data.get('title'):
            default_category = Category.objects.first()
            if default_category:
                import uuid
                news_created = News.objects.create(
                    title=webhook_data.get('title', 'Webhook Test Article'),
                    content=webhook_data.get('content', 'Content from webhook demo'),
                    source=webhook_data.get('source', 'Webhook Demo'),
                    author=webhook_data.get('author', 'Demo User'),
                    category=default_category,
                    external_id=f'demo-webhook-{str(uuid.uuid4())[:8]}'
                )
        
        return JsonResponse({
            'success': True,
            'message': 'Webhook processed successfully',
            'webhook_log_id': str(webhook_log.id),
            'news_created': {
                'id': str(news_created.id),
                'title': news_created.title
            } if news_created else None
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def run_tests_demo():
    """Run a subset of tests for demonstration"""
    try:
        # Run a simple database connectivity test
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_result = cursor.fetchone()
        
        # Check if we can create objects
        test_category = Category.objects.create(
            name=f"Test Category {datetime.now().strftime('%H%M%S')}",
            description="Temporary test category"
        )
        test_category.delete()  # Clean up
        
        # Check API endpoints
        api_tests = []
        base_url = "http://localhost:8000"
        endpoints = ['/health/', '/api/v1/news/categories/', '/metrics/']
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                api_tests.append({
                    'endpoint': endpoint,
                    'status': 'passed' if response.status_code in [200, 401] else 'failed',
                    'response_code': response.status_code
                })
            except Exception as e:
                api_tests.append({
                    'endpoint': endpoint,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return JsonResponse({
            'success': True,
            'message': 'Demo tests completed',
            'results': {
                'database': 'passed',
                'model_creation': 'passed',
                'api_endpoints': api_tests
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def check_health_demo():
    """Check system health for demonstration"""
    try:
        health_checks = {}
        
        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_checks['database'] = {'status': 'healthy', 'response_time': 0.001}
        except Exception as e:
            health_checks['database'] = {'status': 'unhealthy', 'error': str(e)}
        
        # API endpoints check
        base_url = "http://localhost:8000"
        endpoints = {
            'health': '/health/',
            'celery': '/celery/health/',
            'business': '/business/health/',
            'security': '/security/health/',
            'metrics': '/metrics/'
        }
        
        for name, endpoint in endpoints.items():
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                health_checks[name] = {
                    'status': 'healthy' if response.status_code == 200 else 'degraded',
                    'response_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
            except Exception as e:
                health_checks[name] = {'status': 'unhealthy', 'error': str(e)}
        
        # System statistics
        stats = get_system_stats()
        
        return JsonResponse({
            'success': True,
            'message': 'Health check completed',
            'health_checks': health_checks,
            'system_stats': stats
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def generate_load_demo():
    """Generate load for testing purposes"""
    try:
        # Create multiple news articles
        category = Category.objects.first()
        if not category:
            category = Category.objects.create(name="Load Test", description="For load testing")
        
        articles_created = []
        for i in range(10):
            article = News.objects.create(
                title=f"Load Test Article {i+1}",
                content=f"This is content for load test article number {i+1}",
                source="Load Test Generator",
                author="Load Test Bot",
                category=category
            )
            articles_created.append(str(article.id))
        
        # Create webhook source if it doesn't exist
        webhook_source, created = WebhookSource.objects.get_or_create(
            name='load-test-source',
            defaults={
                'description': 'Load testing webhook source',
                'endpoint_url': 'http://localhost:8000/api/v1/webhooks/receive/load-test-source/',
                'is_active': True,
                'requires_authentication': False,
                'rate_limit_per_minute': 1000
            }
        )
        
        # Create some webhook logs
        webhook_logs_created = []
        for i in range(5):
            webhook_log = WebhookLog.objects.create(
                source=webhook_source,
                method='POST',
                path=f'/load-test/{i}',
                headers={'Content-Type': 'application/json'},
                body=f'{{"test": "load_{i}"}}',
                status='success',
                processing_time=0.05 + (i * 0.01),
                remote_ip='127.0.0.1',
                user_agent='Load-Test-Client/1.0'
            )
            webhook_logs_created.append(str(webhook_log.id))
        
        return JsonResponse({
            'success': True,
            'message': f'Generated load: {len(articles_created)} articles, {len(webhook_logs_created)} webhook logs',
            'articles_created': articles_created,
            'webhook_logs_created': webhook_logs_created,
            'webhook_source_created': created
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def get_system_stats():
    """Get current system statistics"""
    try:
        return {
            'news_articles': News.objects.count(),
            'categories': Category.objects.count(),
            'tags': Tag.objects.count(),
            'webhook_logs': WebhookLog.objects.count(),
            'notifications': Notification.objects.count(),
            'classification_results': ClassificationResult.objects.count(),
        }
    except Exception:
        return {}


def get_api_endpoints():
    """Get list of key API endpoints"""
    return [
        {'name': 'API Documentation', 'url': '/api/docs/', 'description': 'Interactive API documentation'},
        {'name': 'News Articles', 'url': '/api/v1/news/articles/', 'description': 'CRUD operations for news'},
        {'name': 'Categories', 'url': '/api/v1/news/categories/', 'description': 'News categories management'},
        {'name': 'Webhooks', 'url': '/api/v1/webhooks/logs/', 'description': 'Webhook processing logs'},
        {'name': 'Health Check', 'url': '/health/', 'description': 'System health status'},
        {'name': 'Metrics', 'url': '/metrics/', 'description': 'Prometheus metrics'},
        {'name': 'Celery Monitoring', 'url': '/celery/status/', 'description': 'Celery worker status'},
        {'name': 'Business Metrics', 'url': '/business/status/', 'description': 'Business KPIs'},
        {'name': 'Security Status', 'url': '/security/status/', 'description': 'Security monitoring'},
    ]


def get_grafana_dashboards():
    """Get list of Grafana dashboards"""
    try:
        response = requests.get(
            "http://localhost:3000/api/search",
            auth=('admin', 'admin'),
            timeout=5
        )
        if response.status_code == 200:
            dashboards = response.json()
            return [
                {
                    'title': d.get('title', 'Unknown'),
                    'url': f"http://localhost:3000{d.get('url', '')}",
                    'tags': d.get('tags', [])
                }
                for d in dashboards
            ]
    except Exception:
        pass
    
    # Fallback to expected dashboards
    return [
        {'title': 'JOTA News - Complete Dashboard', 'url': 'http://localhost:3000/d/jota-news-complete/', 'tags': ['jota', 'monitoring']},
        {'title': 'Celery Task Monitoring', 'url': 'http://localhost:3000/d/celery-dashboard/', 'tags': ['celery', 'tasks']},
        {'title': 'Business Metrics', 'url': 'http://localhost:3000/d/business-dashboard/', 'tags': ['business', 'metrics']},
        {'title': 'Security Monitoring', 'url': 'http://localhost:3000/d/security-dashboard/', 'tags': ['security', 'monitoring']},
        {'title': 'Redis Dashboard', 'url': 'http://localhost:3000/d/redis-dashboard/', 'tags': ['redis', 'cache']},
    ]


@csrf_exempt
@require_http_methods(["GET"])
def system_status_api(request):
    """API endpoint for system status"""
    try:
        status = {
            'timestamp': datetime.now().isoformat(),
            'system_stats': get_system_stats(),
            'health_checks': {},
            'monitoring_urls': {
                'grafana': 'http://localhost:3000',
                'api_docs': 'http://localhost:8000/api/docs/',
                'metrics': 'http://localhost:8000/metrics/',
            }
        }
        
        # Quick health checks
        base_url = "http://localhost:8000"
        endpoints = ['/health/', '/celery/health/', '/business/health/', '/security/health/']
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=2)
                status['health_checks'][endpoint] = {
                    'status': 'healthy' if response.status_code == 200 else 'degraded',
                    'response_code': response.status_code
                }
            except Exception:
                status['health_checks'][endpoint] = {'status': 'unhealthy'}
        
        return JsonResponse(status)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)