#!/usr/bin/env python3
"""
Quick Metrics Generator for JOTA News System
===========================================

A simple, fast script to generate metrics data for Grafana dashboards.
"""

import requests
import time
import random
import subprocess
from datetime import datetime

def print_status(message, color='\033[92m'):
    print(f"{color}[{datetime.now().strftime('%H:%M:%S')}] {message}\033[0m")

def generate_webhooks(count=20):
    """Generate webhook events quickly"""
    print_status(f"🔗 Generating {count} webhook events...")
    
    base_url = "http://localhost:8000"
    categories = ['politica', 'economia', 'tecnologia', 'internacional']
    
    success_count = 0
    for i in range(count):
        try:
            webhook_data = {
                "title": f"Quick Test News #{i+1}",
                "content": f"Quick test content for metrics generation. Article {i+1}",
                "source": "Quick Test",
                "author": "Test Generator",
                "category_hint": random.choice(categories),
                "is_urgent": random.choice([True, False]),
                "external_id": f"quick-test-{i}-{int(time.time())}"
            }
            
            response = requests.post(
                f"{base_url}/api/v1/webhooks/receive/demo-source/",
                json=webhook_data,
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                success_count += 1
            
            if i % 5 == 0:
                print_status(f"  ✓ Webhook {i+1}/{count} sent")
                
        except Exception as e:
            print_status(f"  ✗ Webhook {i+1} failed: {e}", '\033[91m')
            
    print_status(f"✅ Generated {success_count}/{count} webhook events")

def generate_classification_tasks(count=15):
    """Generate classification tasks"""
    print_status(f"🤖 Generating {count} classification tasks...")
    
    success_count = 0
    for i in range(count):
        try:
            cmd = f'''docker-compose exec -T api python manage.py shell -c "
from apps.classification.tasks import classify_news
from apps.news.models import News
import random

news = News.objects.all()
if news:
    article = random.choice(news)
    result = classify_news.delay(article.id)
    print(f'Task queued: {{result.id}}')
else:
    print('No news found')
"'''
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
            
            if result.returncode == 0 and 'Task queued' in result.stdout:
                success_count += 1
                
            if i % 5 == 0:
                print_status(f"  ✓ Classification task {i+1}/{count} queued")
                
        except Exception as e:
            print_status(f"  ✗ Classification task {i+1} failed: {e}", '\033[91m')
            
    print_status(f"✅ Generated {success_count}/{count} classification tasks")

def generate_auth_attempts(count=30):
    """Generate authentication attempts"""
    print_status(f"🔐 Generating {count} authentication attempts...")
    
    base_url = "http://localhost:8000"
    usernames = ['admin', 'user1', 'test_user', 'invalid_user', 'hacker']
    passwords = ['password123', 'admin', 'wrong_password', 'test123']
    
    success_count = 0
    for i in range(count):
        try:
            auth_data = {
                'username': random.choice(usernames),
                'password': random.choice(passwords)
            }
            
            response = requests.post(
                f"{base_url}/api/v1/auth/login/",
                json=auth_data,
                timeout=3
            )
            
            success_count += 1
            
            if i % 10 == 0:
                print_status(f"  ✓ Auth attempt {i+1}/{count}")
                
        except Exception as e:
            print_status(f"  ✗ Auth attempt {i+1} failed: {e}", '\033[91m')
            
    print_status(f"✅ Generated {success_count}/{count} authentication attempts")

def generate_api_traffic(count=40):
    """Generate API traffic"""
    print_status(f"📡 Generating {count} API calls...")
    
    base_url = "http://localhost:8000"
    endpoints = [
        '/api/v1/news/articles/',
        '/api/v1/news/categories/',
        '/health/',
        '/metrics',
        '/celery/health/',
        '/business/health/',
        '/security/health/',
    ]
    
    success_count = 0
    for i in range(count):
        try:
            endpoint = random.choice(endpoints)
            response = requests.get(f"{base_url}{endpoint}", timeout=3)
            
            success_count += 1
            
            if i % 15 == 0:
                print_status(f"  ✓ API call {i+1}/{count} - {endpoint}")
                
        except Exception as e:
            print_status(f"  ✗ API call {i+1} failed: {e}", '\033[91m')
            
    print_status(f"✅ Generated {success_count}/{count} API calls")

def wait_for_processing():
    """Wait for tasks to be processed"""
    print_status("⏳ Waiting for tasks to be processed...")
    time.sleep(15)  # Wait 15 seconds for processing

def check_metrics():
    """Check if metrics are now available"""
    print_status("📊 Checking metrics availability...")
    
    try:
        # Check celery metrics
        response = requests.get("http://localhost:9090/api/v1/query?query=celery_tasks_total", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('data', {}).get('result'):
                print_status("✅ Celery metrics are now available!")
            else:
                print_status("⚠ Celery metrics still empty", '\033[93m')
        
        # Check news metrics
        response = requests.get("http://localhost:9090/api/v1/query?query=jota_news_articles_total", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('data', {}).get('result'):
                print_status("✅ News metrics are available!")
            else:
                print_status("⚠ News metrics still empty", '\033[93m')
                
        # Check webhook metrics
        response = requests.get("http://localhost:9090/api/v1/query?query=jota_webhooks_events_total", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('data', {}).get('result'):
                print_status("✅ Webhook metrics are available!")
            else:
                print_status("⚠ Webhook metrics still empty", '\033[93m')
                
    except Exception as e:
        print_status(f"✗ Error checking metrics: {e}", '\033[91m')

def main():
    print("\033[95m\033[1m")
    print("🚀 JOTA News System - Quick Metrics Generator")
    print("=" * 50)
    print("Target: Fill empty Grafana dashboards quickly")
    print("=" * 50)
    print("\033[0m")
    
    start_time = datetime.now()
    
    # Generate activity in parallel where possible
    generate_webhooks(20)
    time.sleep(2)
    
    generate_classification_tasks(15)
    time.sleep(2)
    
    generate_auth_attempts(30)
    time.sleep(2)
    
    generate_api_traffic(40)
    
    wait_for_processing()
    check_metrics()
    
    duration = (datetime.now() - start_time).total_seconds()
    
    print(f"\n\033[92m{'='*50}")
    print(f"✅ QUICK METRICS GENERATION COMPLETED")
    print(f"{'='*50}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"📊 Check your Grafana dashboards now!")
    print(f"🌐 Grafana: http://localhost:3000")
    print(f"📈 Metrics: http://localhost:8000/metrics")
    print(f"{'='*50}\033[0m")

if __name__ == "__main__":
    main()