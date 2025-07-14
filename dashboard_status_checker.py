#!/usr/bin/env python3
"""
Dashboard Status Checker for JOTA News System
===========================================

Checks the status of all Grafana dashboards and provides solutions for empty ones.
"""

import requests
import json
import time
from datetime import datetime

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_status(message, color=Colors.OKGREEN):
    print(f"{color}{message}{Colors.ENDC}")

def check_prometheus_targets():
    """Check if Prometheus targets are healthy"""
    print_status("🎯 Checking Prometheus targets...", Colors.OKCYAN)
    
    try:
        response = requests.get("http://localhost:9090/api/v1/targets", timeout=10)
        if response.status_code == 200:
            data = response.json()
            targets = data.get('data', {}).get('activeTargets', [])
            
            healthy_targets = [t for t in targets if t.get('health') == 'up']
            
            print_status(f"✅ Total targets: {len(targets)}")
            print_status(f"✅ Healthy targets: {len(healthy_targets)}")
            
            # Check specific Django targets
            django_targets = [t for t in targets if 'django' in t.get('labels', {}).get('job', '')]
            for target in django_targets:
                job = target.get('labels', {}).get('job', '')
                health = target.get('health', '')
                scrape_interval = target.get('scrapeInterval', '')
                last_scrape = target.get('lastScrape', '')
                
                status_color = Colors.OKGREEN if health == 'up' else Colors.FAIL
                print_status(f"  {job}: {health} (interval: {scrape_interval})", status_color)
                
            return len(healthy_targets) == len(targets)
        else:
            print_status(f"❌ Cannot connect to Prometheus: {response.status_code}", Colors.FAIL)
            return False
            
    except Exception as e:
        print_status(f"❌ Error checking Prometheus: {e}", Colors.FAIL)
        return False

def check_metrics_availability():
    """Check if key metrics are available"""
    print_status("\n📊 Checking metrics availability...", Colors.OKCYAN)
    
    metrics_to_check = [
        ("jota_news_articles_total", "News Articles"),
        ("jota_webhooks_events_total", "Webhook Events"),
        ("celery_tasks_total", "Celery Tasks"),
        ("jota_authentication_attempts_total", "Authentication Attempts"),
        ("jota_security_events_total", "Security Events"),
        ("django_http_requests_total", "HTTP Requests"),
        ("redis_connected_clients", "Redis Clients"),
        ("postgres_up", "PostgreSQL Status")
    ]
    
    available_metrics = []
    
    for metric_name, display_name in metrics_to_check:
        try:
            response = requests.get(
                f"http://localhost:9090/api/v1/query?query={metric_name}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('data', {}).get('result', [])
                
                if results:
                    # Get total value across all results
                    total_value = sum(float(result.get('value', [0, 0])[1]) for result in results)
                    print_status(f"✅ {display_name}: {total_value:.0f}")
                    available_metrics.append(metric_name)
                else:
                    print_status(f"⚠ {display_name}: No data", Colors.WARNING)
            else:
                print_status(f"❌ {display_name}: Query failed", Colors.FAIL)
                
        except Exception as e:
            print_status(f"❌ {display_name}: Error - {e}", Colors.FAIL)
    
    return available_metrics

def check_grafana_dashboards():
    """Check Grafana dashboard availability"""
    print_status("\n📈 Checking Grafana dashboards...", Colors.OKCYAN)
    
    try:
        response = requests.get(
            "http://localhost:3000/api/search",
            auth=('admin', 'admin'),
            timeout=10
        )
        
        if response.status_code == 200:
            dashboards = response.json()
            print_status(f"✅ Found {len(dashboards)} Grafana dashboards")
            
            for dashboard in dashboards:
                title = dashboard.get('title', 'Unknown')
                uid = dashboard.get('uid', 'Unknown')
                url = f"http://localhost:3000/d/{uid}"
                print_status(f"  📊 {title}: {url}")
                
            return True
        else:
            print_status(f"❌ Cannot connect to Grafana: {response.status_code}", Colors.FAIL)
            return False
            
    except Exception as e:
        print_status(f"❌ Error checking Grafana: {e}", Colors.FAIL)
        return False

def show_dashboard_urls():
    """Show direct URLs to dashboards"""
    print_status("\n🌐 Quick Dashboard Access:", Colors.HEADER)
    
    dashboards = [
        ("Complete Dashboard", "jota-news-complete"),
        ("Celery Monitoring", "celery-dashboard"),
        ("Business Metrics", "business-dashboard"),
        ("Security Monitoring", "security-dashboard"),
        ("Redis Performance", "redis-dashboard"),
    ]
    
    for name, uid in dashboards:
        url = f"http://localhost:3000/d/{uid}"
        print_status(f"  📊 {name}: {url}", Colors.OKBLUE)

def provide_recommendations():
    """Provide recommendations for empty dashboards"""
    print_status("\n💡 Recommendations for Empty Dashboards:", Colors.HEADER)
    
    recommendations = [
        "1. Run the quick metrics generator:",
        "   python3 quick_metrics_generator.py",
        "",
        "2. Generate more activity with the populate script:",
        "   ./populate_dashboards.sh",
        "",
        "3. For continuous metrics generation:",
        "   python3 stress_test_metrics.py --continuous",
        "",
        "4. Check if Celery worker is running:",
        "   docker-compose logs worker",
        "",
        "5. Restart services if needed:",
        "   docker-compose restart worker beat",
        "",
        "6. Wait 2-3 minutes after generating activity",
        "   (Prometheus scrapes every 3-5 seconds now)",
        "",
        "7. Refresh your Grafana dashboards manually",
        "   (Use Ctrl+R or the refresh button)",
    ]
    
    for rec in recommendations:
        print_status(rec, Colors.OKCYAN)

def main():
    print_status(f"{Colors.HEADER}{Colors.BOLD}")
    print_status("🗞️  JOTA News System - Dashboard Status Checker")
    print_status("=" * 60)
    print_status(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_status("=" * 60)
    print_status(f"{Colors.ENDC}")
    
    # Check system components
    prometheus_healthy = check_prometheus_targets()
    available_metrics = check_metrics_availability()
    grafana_healthy = check_grafana_dashboards()
    
    # Show dashboard URLs
    show_dashboard_urls()
    
    # Provide recommendations
    provide_recommendations()
    
    # Summary
    print_status(f"\n{Colors.HEADER}📋 SUMMARY:{Colors.ENDC}")
    print_status(f"✅ Prometheus: {'Healthy' if prometheus_healthy else 'Issues detected'}")
    print_status(f"✅ Grafana: {'Healthy' if grafana_healthy else 'Issues detected'}")
    print_status(f"✅ Available metrics: {len(available_metrics)}/8")
    
    if len(available_metrics) < 4:
        print_status(f"\n{Colors.WARNING}⚠ LOW METRICS DETECTED{Colors.ENDC}")
        print_status("Run: python3 quick_metrics_generator.py")
    else:
        print_status(f"\n{Colors.OKGREEN}✅ METRICS LOOK GOOD{Colors.ENDC}")
        print_status("Your dashboards should have data now!")
    
    print_status(f"\n{Colors.OKCYAN}🎯 Next Steps:{Colors.ENDC}")
    print_status("1. Open Grafana: http://localhost:3000 (admin/admin)")
    print_status("2. Navigate to your dashboards")
    print_status("3. If still empty, run the quick metrics generator")
    print_status("4. Wait 2-3 minutes for data to appear")

if __name__ == "__main__":
    main()