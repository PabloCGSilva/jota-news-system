#!/usr/bin/env python3
"""
JOTA News System - Metrics Stress Test Generator
===============================================

This script generates intensive activity to populate all Grafana dashboard metrics
quickly. It creates realistic load to test the system and fill empty dashboards.

Usage:
    python3 stress_test_metrics.py --quick      # 2-minute quick test
    python3 stress_test_metrics.py --full       # 10-minute comprehensive test
    python3 stress_test_metrics.py --continuous # Run until stopped
"""

import os
import sys
import time
import json
import random
import argparse
import threading
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class MetricsStressTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.stats = {
            'webhooks_sent': 0,
            'classification_tasks': 0,
            'auth_attempts': 0,
            'api_calls': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        self.running = True
        
    def print_status(self, message, color=Colors.OKGREEN):
        print(f"{color}[{datetime.now().strftime('%H:%M:%S')}] {message}{Colors.ENDC}")
        
    def print_stats(self):
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        print(f"\n{Colors.OKCYAN}{'='*60}")
        print(f"  METRICS STRESS TEST - LIVE STATS")
        print(f"{'='*60}")
        print(f"Duration: {duration:.1f}s")
        print(f"Webhooks Sent: {self.stats['webhooks_sent']}")
        print(f"Classification Tasks: {self.stats['classification_tasks']}")
        print(f"Auth Attempts: {self.stats['auth_attempts']}")
        print(f"API Calls: {self.stats['api_calls']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Rate: {(self.stats['webhooks_sent'] + self.stats['classification_tasks'])/(duration or 1):.1f} ops/sec")
        print(f"{'='*60}{Colors.ENDC}")

    def generate_webhook_events(self, count=10):
        """Generate webhook events to populate webhook metrics"""
        webhook_sources = ['demo-source', 'test-source', 'load-test-source']
        categories = ['politica', 'economia', 'tecnologia', 'internacional', 'justica']
        
        for i in range(count):
            try:
                source = random.choice(webhook_sources)
                category = random.choice(categories)
                
                webhook_data = {
                    "title": f"Stress Test News #{i+1} - {category.title()}",
                    "content": f"This is a stress test article for category {category}. Generated at {datetime.now().isoformat()}. This content is designed to test the webhook processing pipeline and generate metrics for monitoring dashboards.",
                    "source": f"Stress Test - {source}",
                    "author": f"Test User {random.randint(1,10)}",
                    "category_hint": category,
                    "is_urgent": random.choice([True, False, False]),  # 33% urgent
                    "external_id": f"stress-test-{i}-{int(time.time())}"
                }
                
                response = requests.post(
                    f"{self.base_url}/api/v1/webhooks/receive/{source}/",
                    json=webhook_data,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    self.stats['webhooks_sent'] += 1
                    if i % 5 == 0:
                        self.print_status(f"✓ Webhook {i+1}/{count} sent successfully")
                else:
                    self.stats['errors'] += 1
                    if i % 10 == 0:
                        self.print_status(f"⚠ Webhook {i+1} failed: {response.status_code}", Colors.WARNING)
                        
            except Exception as e:
                self.stats['errors'] += 1
                if i % 10 == 0:
                    self.print_status(f"✗ Webhook {i+1} error: {e}", Colors.FAIL)
                    
            # Small delay to avoid overwhelming the system
            time.sleep(0.1)

    def generate_classification_tasks(self, count=10):
        """Generate classification tasks to populate Celery metrics"""
        try:
            # First, ensure we have some news articles
            response = requests.get(f"{self.base_url}/api/v1/news/articles/", timeout=10)
            if response.status_code != 200:
                self.print_status("⚠ Cannot fetch news articles for classification", Colors.WARNING)
                return
                
            articles = response.json().get('results', [])
            if not articles:
                self.print_status("⚠ No news articles found for classification", Colors.WARNING)
                return
                
            # Generate classification tasks
            import subprocess
            for i in range(count):
                try:
                    article = random.choice(articles)
                    article_id = article['id']
                    
                    # Queue classification task via Django shell
                    cmd = f'''docker-compose exec -T api python manage.py shell -c "
from apps.classification.tasks import classify_news
result = classify_news.delay({article_id})
print('Task queued:', result.id)
"'''
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        self.stats['classification_tasks'] += 1
                        if i % 5 == 0:
                            self.print_status(f"✓ Classification task {i+1}/{count} queued")
                    else:
                        self.stats['errors'] += 1
                        if i % 10 == 0:
                            self.print_status(f"⚠ Classification task {i+1} failed", Colors.WARNING)
                            
                except Exception as e:
                    self.stats['errors'] += 1
                    if i % 10 == 0:
                        self.print_status(f"✗ Classification task {i+1} error: {e}", Colors.FAIL)
                        
                time.sleep(0.2)  # Slight delay between tasks
                
        except Exception as e:
            self.print_status(f"✗ Classification task generation failed: {e}", Colors.FAIL)

    def generate_auth_attempts(self, count=20):
        """Generate authentication attempts to populate security metrics"""
        usernames = ['admin', 'user1', 'user2', 'test_user', 'invalid_user', 'hacker', 'guest']
        passwords = ['password123', 'admin', 'wrong_password', 'test123', '123456', 'admin123']
        
        for i in range(count):
            try:
                username = random.choice(usernames)
                password = random.choice(passwords)
                
                # Try to authenticate (this will generate security metrics)
                auth_data = {
                    'username': username,
                    'password': password
                }
                
                response = requests.post(
                    f"{self.base_url}/api/v1/auth/login/",
                    json=auth_data,
                    timeout=5
                )
                
                self.stats['auth_attempts'] += 1
                
                if i % 10 == 0:
                    status = "success" if response.status_code == 200 else "failed"
                    self.print_status(f"✓ Auth attempt {i+1}/{count} ({status})")
                    
            except Exception as e:
                self.stats['errors'] += 1
                if i % 10 == 0:
                    self.print_status(f"✗ Auth attempt {i+1} error: {e}", Colors.FAIL)
                    
            time.sleep(0.1)

    def generate_api_traffic(self, count=50):
        """Generate API traffic to populate general metrics"""
        endpoints = [
            '/api/v1/news/articles/',
            '/api/v1/news/categories/',
            '/api/v1/news/tags/',
            '/health/',
            '/metrics',
            '/celery/health/',
            '/business/health/',
            '/security/health/',
            '/api/v1/news/articles/?category=politics',
            '/api/v1/news/articles/?is_urgent=true',
        ]
        
        for i in range(count):
            try:
                endpoint = random.choice(endpoints)
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                
                self.stats['api_calls'] += 1
                
                if i % 20 == 0:
                    self.print_status(f"✓ API call {i+1}/{count} - {endpoint}")
                    
            except Exception as e:
                self.stats['errors'] += 1
                if i % 20 == 0:
                    self.print_status(f"✗ API call {i+1} error: {e}", Colors.FAIL)
                    
            time.sleep(0.05)  # Very fast API calls

    def generate_notification_events(self, count=15):
        """Generate notification events to populate notification metrics"""
        try:
            import subprocess
            
            for i in range(count):
                try:
                    # Generate notification via Django shell
                    cmd = f'''docker-compose exec -T api python manage.py shell -c "
from apps.notifications.tasks import send_notification_task
from apps.notifications.models import NotificationChannel
import random

# Try to get a notification channel
channels = list(NotificationChannel.objects.all())
if channels:
    channel = random.choice(channels)
    result = send_notification_task.delay(
        channel_id=channel.id,
        title='Stress Test Notification #{i+1}',
        message='This is a test notification for metrics generation',
        priority='medium'
    )
    print('Notification task queued:', result.id)
else:
    print('No notification channels available')
"'''
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        if i % 5 == 0:
                            self.print_status(f"✓ Notification {i+1}/{count} queued")
                    else:
                        self.stats['errors'] += 1
                        
                except Exception as e:
                    self.stats['errors'] += 1
                    if i % 10 == 0:
                        self.print_status(f"✗ Notification {i+1} error: {e}", Colors.FAIL)
                        
                time.sleep(0.3)
                
        except Exception as e:
            self.print_status(f"✗ Notification generation failed: {e}", Colors.FAIL)

    def run_stress_test(self, duration_minutes=5):
        """Run the complete stress test for specified duration"""
        
        print(f"{Colors.HEADER}{Colors.BOLD}")
        print("🔥 JOTA NEWS SYSTEM - METRICS STRESS TEST")
        print("=" * 50)
        print(f"Duration: {duration_minutes} minutes")
        print(f"Target: Fill all empty Grafana dashboards")
        print("=" * 50)
        print(f"{Colors.ENDC}")
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        cycle = 0
        
        while datetime.now() < end_time and self.running:
            cycle += 1
            self.print_status(f"🔄 Starting cycle {cycle}")
            
            # Use ThreadPoolExecutor for parallel execution
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                
                # Submit all tasks in parallel
                futures.append(executor.submit(self.generate_webhook_events, 15))
                futures.append(executor.submit(self.generate_classification_tasks, 8))
                futures.append(executor.submit(self.generate_auth_attempts, 12))
                futures.append(executor.submit(self.generate_api_traffic, 30))
                futures.append(executor.submit(self.generate_notification_events, 5))
                
                # Wait for all tasks to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.print_status(f"✗ Task error: {e}", Colors.FAIL)
                        self.stats['errors'] += 1
            
            # Show stats every cycle
            self.print_stats()
            
            # Wait before next cycle
            time.sleep(5)
            
            # Check if we should continue
            if cycle >= 20:  # Safety limit
                self.print_status("⚠ Reached maximum cycles, stopping", Colors.WARNING)
                break
                
        self.print_final_stats()
        
    def print_final_stats(self):
        """Print final statistics"""
        total_duration = (datetime.now() - self.stats['start_time']).total_seconds()
        
        print(f"\n{Colors.OKGREEN}{'='*60}")
        print(f"  STRESS TEST COMPLETED")
        print(f"{'='*60}")
        print(f"Total Duration: {total_duration:.1f} seconds")
        print(f"Total Webhooks: {self.stats['webhooks_sent']}")
        print(f"Total Classification Tasks: {self.stats['classification_tasks']}")
        print(f"Total Auth Attempts: {self.stats['auth_attempts']}")
        print(f"Total API Calls: {self.stats['api_calls']}")
        print(f"Total Errors: {self.stats['errors']}")
        print(f"Average Rate: {(self.stats['webhooks_sent'] + self.stats['classification_tasks'])/(total_duration or 1):.2f} ops/sec")
        print(f"{'='*60}")
        print(f"🎯 Check your Grafana dashboards now!")
        print(f"📊 Dashboards: http://localhost:3000")
        print(f"📈 Metrics: http://localhost:8000/metrics")
        print(f"{'='*60}{Colors.ENDC}")

    def quick_test(self):
        """Run a quick 2-minute test"""
        self.run_stress_test(duration_minutes=2)
        
    def full_test(self):
        """Run a comprehensive 10-minute test"""
        self.run_stress_test(duration_minutes=10)
        
    def continuous_test(self):
        """Run until manually stopped"""
        self.print_status("🔄 Running continuous stress test. Press Ctrl+C to stop.", Colors.OKCYAN)
        try:
            while self.running:
                self.run_stress_test(duration_minutes=60)  # 1 hour chunks
        except KeyboardInterrupt:
            self.print_status("🛑 Stress test stopped by user", Colors.WARNING)
            self.running = False

def main():
    parser = argparse.ArgumentParser(description="JOTA News System Metrics Stress Tester")
    parser.add_argument('--quick', action='store_true', help='Run quick 2-minute test')
    parser.add_argument('--full', action='store_true', help='Run full 10-minute test')
    parser.add_argument('--continuous', action='store_true', help='Run continuous test')
    
    args = parser.parse_args()
    
    tester = MetricsStressTester()
    
    try:
        if args.quick:
            tester.quick_test()
        elif args.full:
            tester.full_test()
        elif args.continuous:
            tester.continuous_test()
        else:
            # Default: quick test
            print("No mode specified. Running quick test (2 minutes)...")
            print("Use --help to see all options")
            tester.quick_test()
            
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}🛑 Stress test interrupted by user{Colors.ENDC}")
        tester.running = False
    except Exception as e:
        print(f"{Colors.FAIL}✗ Stress test failed: {e}{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()