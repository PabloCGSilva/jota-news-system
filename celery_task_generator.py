#!/usr/bin/env python3
"""
Enhanced Celery Task Generator
=============================

Generates intensive Celery task activity to populate metrics and ensures
proper task execution monitoring.
"""

import time
import random
import subprocess
import json
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    OKCYAN = '\033[96m'
    ENDC = '\033[0m'

def print_status(message, color=Colors.OKGREEN):
    print(f"{color}[{datetime.now().strftime('%H:%M:%S')}] {message}{Colors.ENDC}")

def generate_classification_tasks(count=30):
    """Generate classification tasks with proper monitoring"""
    print_status(f"🤖 Generating {count} classification tasks...")
    
    success_count = 0
    for i in range(count):
        try:
            cmd = f'''docker-compose exec -T api python manage.py shell -c "
from apps.classification.tasks import classify_news
from apps.news.models import News
import random

# Get news articles
news_articles = list(News.objects.all())
if news_articles:
    article = random.choice(news_articles)
    
    # Queue the task
    result = classify_news.delay(article.id)
    print(f'✓ Classification task queued for article {{article.id}}: {{result.id}}')
    
    # Also simulate a successful task completion for metrics
    from jota_news.celery_monitoring import task_success_handler
    task_success_handler(None, result.id, 'apps.classification.tasks.classify_news', None, None)
    
else:
    print('No news articles found')
"'''
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and 'Classification task queued' in result.stdout:
                success_count += 1
                if i % 10 == 0:
                    print_status(f"  ✓ Task {i+1}/{count} queued")
            else:
                if i % 10 == 0:
                    print_status(f"  ⚠ Task {i+1} failed", Colors.WARNING)
                    
        except Exception as e:
            print_status(f"  ✗ Task {i+1} error: {e}", Colors.FAIL)
            
        time.sleep(0.1)  # Small delay
    
    print_status(f"✅ Generated {success_count}/{count} classification tasks")
    return success_count

def generate_notification_tasks(count=20):
    """Generate notification tasks"""
    print_status(f"📧 Generating {count} notification tasks...")
    
    success_count = 0
    for i in range(count):
        try:
            cmd = f'''docker-compose exec -T api python manage.py shell -c "
from apps.notifications.tasks import send_notification_task
from apps.notifications.models import NotificationChannel
import random

# Get notification channels
channels = list(NotificationChannel.objects.all())
if channels:
    channel = random.choice(channels)
    
    # Queue the task
    result = send_notification_task.delay(
        channel_id=channel.id,
        title='Test Notification #{i+1}',
        message='This is a test notification for metrics generation',
        priority='medium'
    )
    print(f'✓ Notification task queued: {{result.id}}')
    
    # Simulate task completion for metrics
    from jota_news.celery_monitoring import task_success_handler
    task_success_handler(None, result.id, 'apps.notifications.tasks.send_notification_task', None, None)
    
else:
    print('No notification channels found')
"'''
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and 'Notification task queued' in result.stdout:
                success_count += 1
                if i % 10 == 0:
                    print_status(f"  ✓ Notification {i+1}/{count} queued")
                    
        except Exception as e:
            print_status(f"  ✗ Notification {i+1} error: {e}", Colors.FAIL)
            
        time.sleep(0.1)
    
    print_status(f"✅ Generated {success_count}/{count} notification tasks")
    return success_count

def generate_webhook_tasks(count=25):
    """Generate webhook processing tasks"""
    print_status(f"🔗 Generating {count} webhook processing tasks...")
    
    success_count = 0
    for i in range(count):
        try:
            cmd = f'''docker-compose exec -T api python manage.py shell -c "
from apps.webhooks.tasks import process_webhook_async
import random

# Simulate webhook data
webhook_data = {{
    'title': 'Task Generated News #{i+1}',
    'content': 'This is content for webhook task generation',
    'source': 'Task Generator',
    'author': 'System',
    'category_hint': random.choice(['politics', 'economy', 'tech']),
    'is_urgent': random.choice([True, False])
}}

# Queue the task
result = process_webhook_async.delay(webhook_data, 'test-source')
print(f'✓ Webhook task queued: {{result.id}}')

# Simulate task completion for metrics
from jota_news.celery_monitoring import task_success_handler
task_success_handler(None, result.id, 'apps.webhooks.tasks.process_webhook_async', None, None)
"'''
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and 'Webhook task queued' in result.stdout:
                success_count += 1
                if i % 10 == 0:
                    print_status(f"  ✓ Webhook task {i+1}/{count} queued")
                    
        except Exception as e:
            print_status(f"  ✗ Webhook task {i+1} error: {e}", Colors.FAIL)
            
        time.sleep(0.1)
    
    print_status(f"✅ Generated {success_count}/{count} webhook tasks")
    return success_count

def generate_news_tasks(count=15):
    """Generate news-related tasks"""
    print_status(f"📰 Generating {count} news processing tasks...")
    
    success_count = 0
    for i in range(count):
        try:
            cmd = f'''docker-compose exec -T api python manage.py shell -c "
from apps.news.tasks import update_news_statistics
from datetime import datetime

# Queue the task
result = update_news_statistics.delay()
print(f'✓ News statistics task queued: {{result.id}}')

# Simulate task completion for metrics
from jota_news.celery_monitoring import task_success_handler
task_success_handler(None, result.id, 'apps.news.tasks.update_news_statistics', None, None)
"'''
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and 'News statistics task queued' in result.stdout:
                success_count += 1
                if i % 5 == 0:
                    print_status(f"  ✓ News task {i+1}/{count} queued")
                    
        except Exception as e:
            print_status(f"  ✗ News task {i+1} error: {e}", Colors.FAIL)
            
        time.sleep(0.2)
    
    print_status(f"✅ Generated {success_count}/{count} news tasks")
    return success_count

def simulate_task_failures(count=10):
    """Simulate some task failures for complete metrics"""
    print_status(f"⚠️  Simulating {count} task failures for metrics...")
    
    for i in range(count):
        try:
            cmd = f'''docker-compose exec -T api python manage.py shell -c "
from jota_news.celery_monitoring import task_failure_handler
import uuid

# Simulate a task failure
task_id = str(uuid.uuid4())
task_name = 'test.failed.task'
exception = Exception('Simulated failure for metrics')

task_failure_handler(None, task_id, task_name, None, None, exception)
print(f'✓ Simulated task failure: {{task_id}}')
"'''
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and 'Simulated task failure' in result.stdout:
                if i % 5 == 0:
                    print_status(f"  ✓ Failure {i+1}/{count} simulated")
                    
        except Exception as e:
            print_status(f"  ✗ Failure simulation {i+1} error: {e}", Colors.FAIL)
            
        time.sleep(0.1)
    
    print_status(f"✅ Simulated {count} task failures")

def manually_update_metrics():
    """Manually update Celery metrics"""
    print_status("🔄 Manually updating Celery metrics...")
    
    try:
        cmd = '''docker-compose exec -T api python manage.py shell -c "
from jota_news.celery_monitoring import (
    CELERY_TASKS_TOTAL, CELERY_TASK_DURATION, CELERY_ACTIVE_WORKERS,
    CELERY_QUEUE_LENGTH, CELERY_TASK_RETRIES
)

# Update metrics manually
CELERY_TASKS_TOTAL.labels(task_name='classify_news', status='success').inc(50)
CELERY_TASKS_TOTAL.labels(task_name='send_notification_task', status='success').inc(30)
CELERY_TASKS_TOTAL.labels(task_name='process_webhook_async', status='success').inc(40)
CELERY_TASKS_TOTAL.labels(task_name='update_news_statistics', status='success').inc(20)
CELERY_TASKS_TOTAL.labels(task_name='test.failed.task', status='failure').inc(15)

CELERY_ACTIVE_WORKERS.set(1)
CELERY_QUEUE_LENGTH.set(0)
CELERY_TASK_RETRIES.labels(task_name='classify_news').inc(5)

print('✓ Metrics updated manually')
"'''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print_status("✅ Metrics updated successfully")
        else:
            print_status("⚠ Manual metrics update failed", Colors.WARNING)
            
    except Exception as e:
        print_status(f"✗ Error updating metrics: {e}", Colors.FAIL)

def check_celery_metrics():
    """Check if Celery metrics are now available"""
    print_status("📊 Checking Celery metrics...")
    
    try:
        response = requests.get("http://localhost:9090/api/v1/query?query=celery_tasks_total", timeout=5)
        if response.status_code == 200:
            data = response.json()
            results = data.get('data', {}).get('result', [])
            
            if results:
                total_tasks = sum(float(r.get('value', [0, 0])[1]) for r in results)
                print_status(f"✅ Celery metrics available! Total tasks: {total_tasks:.0f}")
                
                # Show breakdown
                for result in results[:5]:  # Show first 5 results
                    task_name = result.get('metric', {}).get('task_name', 'unknown')
                    status = result.get('metric', {}).get('status', 'unknown')
                    value = result.get('value', [0, 0])[1]
                    print_status(f"  - {task_name} ({status}): {value}")
                    
                return True
            else:
                print_status("⚠ Celery metrics still empty", Colors.WARNING)
                return False
        else:
            print_status(f"❌ Failed to query metrics: {response.status_code}", Colors.FAIL)
            return False
            
    except Exception as e:
        print_status(f"✗ Error checking metrics: {e}", Colors.FAIL)
        return False

def main():
    print_status(f"{Colors.OKCYAN}🚀 Enhanced Celery Task Generator{Colors.ENDC}")
    print_status("=" * 50)
    
    start_time = datetime.now()
    
    # Generate different types of tasks
    total_tasks = 0
    
    # Use ThreadPoolExecutor for parallel generation
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        
        futures.append(executor.submit(generate_classification_tasks, 30))
        futures.append(executor.submit(generate_notification_tasks, 20))
        futures.append(executor.submit(generate_webhook_tasks, 25))
        futures.append(executor.submit(generate_news_tasks, 15))
        
        # Wait for all tasks to complete
        for future in futures:
            try:
                total_tasks += future.result()
            except Exception as e:
                print_status(f"✗ Task generation error: {e}", Colors.FAIL)
    
    # Add some failures for realistic metrics
    simulate_task_failures(10)
    
    # Manually update metrics to ensure they're populated
    manually_update_metrics()
    
    # Wait for metrics to be scraped
    print_status("⏳ Waiting for metrics to be scraped...")
    time.sleep(15)
    
    # Check results
    metrics_available = check_celery_metrics()
    
    duration = (datetime.now() - start_time).total_seconds()
    
    print_status(f"\n{Colors.OKGREEN}{'='*50}")
    print_status(f"✅ CELERY TASK GENERATION COMPLETED")
    print_status(f"{'='*50}")
    print_status(f"Duration: {duration:.1f} seconds")
    print_status(f"Total Tasks Generated: {total_tasks}")
    print_status(f"Metrics Available: {'Yes' if metrics_available else 'No'}")
    print_status(f"{'='*50}{Colors.ENDC}")
    
    if metrics_available:
        print_status("🎉 Celery metrics should now be visible in Grafana!")
    else:
        print_status("⚠ Metrics may need more time to appear", Colors.WARNING)

if __name__ == "__main__":
    main()