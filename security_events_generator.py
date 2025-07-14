#!/usr/bin/env python3
"""
Security Events Generator for JOTA News System
=============================================

Generates security events and authentication activity to populate 
security monitoring dashboards.
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

def generate_authentication_attempts(count=50):
    """Generate authentication attempts with both successes and failures"""
    print_status(f"🔐 Generating {count} authentication attempts...")
    
    base_url = "http://localhost:8000"
    
    # Mix of valid and invalid credentials
    test_credentials = [
        ("admin", "admin123", True),  # Valid admin
        ("admin", "wrong_password", False),  # Invalid password
        ("user1", "password123", False),  # Invalid user
        ("test_user", "test123", False),  # Invalid user
        ("hacker", "password", False),  # Invalid user
        ("guest", "guest123", False),  # Invalid user
        ("", "", False),  # Empty credentials
        ("admin", "", False),  # Empty password
        ("", "admin123", False),  # Empty username
    ]
    
    success_count = 0
    auth_events = []
    
    for i in range(count):
        try:
            # Pick random credentials
            username, password, is_valid = random.choice(test_credentials)
            
            # Try to authenticate
            auth_data = {
                'username': username,
                'password': password
            }
            
            response = requests.post(
                f"{base_url}/api/v1/auth/login/",
                json=auth_data,
                timeout=5
            )
            
            # Record the event
            event_type = "success" if response.status_code == 200 else "failure"
            auth_events.append({
                'username': username,
                'success': response.status_code == 200,
                'timestamp': datetime.now().isoformat(),
                'ip': '127.0.0.1',
                'user_agent': 'Security Test Generator'
            })
            
            success_count += 1
            
            if i % 10 == 0:
                print_status(f"  ✓ Auth attempt {i+1}/{count} - {event_type}")
                
        except Exception as e:
            print_status(f"  ✗ Auth attempt {i+1} error: {e}", Colors.FAIL)
            
        time.sleep(0.05)  # Small delay
    
    print_status(f"✅ Generated {success_count}/{count} authentication attempts")
    return auth_events

def generate_failed_login_attempts(count=30):
    """Generate failed login attempts for security monitoring"""
    print_status(f"🚫 Generating {count} failed login attempts...")
    
    base_url = "http://localhost:8000"
    
    # Common attack patterns
    attack_patterns = [
        ("admin", "admin"),
        ("admin", "password"),
        ("admin", "123456"),
        ("root", "root"),
        ("user", "user"),
        ("test", "test"),
        ("administrator", "administrator"),
        ("guest", "guest"),
        ("admin", ""),
        ("", "password"),
    ]
    
    failed_attempts = []
    
    for i in range(count):
        try:
            username, password = random.choice(attack_patterns)
            
            auth_data = {
                'username': username,
                'password': password
            }
            
            response = requests.post(
                f"{base_url}/api/v1/auth/login/",
                json=auth_data,
                timeout=5
            )
            
            if response.status_code != 200:
                failed_attempts.append({
                    'username': username,
                    'timestamp': datetime.now().isoformat(),
                    'ip': f"192.168.1.{random.randint(1, 255)}",
                    'user_agent': random.choice([
                        'Mozilla/5.0 (Hacker)',
                        'curl/7.68.0',
                        'Python-requests/2.25.1',
                        'Postman Runtime/7.28.0'
                    ])
                })
            
            if i % 10 == 0:
                print_status(f"  ✓ Failed login {i+1}/{count}")
                
        except Exception as e:
            print_status(f"  ✗ Failed login {i+1} error: {e}", Colors.FAIL)
            
        time.sleep(0.05)
    
    print_status(f"✅ Generated {len(failed_attempts)} failed login attempts")
    return failed_attempts

def generate_rate_limit_violations(count=25):
    """Generate rate limit violations"""
    print_status(f"🚦 Generating {count} rate limit violations...")
    
    base_url = "http://localhost:8000"
    
    # Make rapid requests to trigger rate limiting
    violations = []
    
    for i in range(count):
        try:
            # Make rapid requests to the same endpoint
            for _ in range(5):  # 5 rapid requests
                response = requests.get(
                    f"{base_url}/api/v1/news/articles/",
                    timeout=2
                )
                
                if response.status_code == 429:  # Rate limited
                    violations.append({
                        'endpoint': '/api/v1/news/articles/',
                        'ip': f"10.0.0.{random.randint(1, 255)}",
                        'timestamp': datetime.now().isoformat()
                    })
                    
                time.sleep(0.01)  # Very small delay
            
            if i % 10 == 0:
                print_status(f"  ✓ Rate limit test {i+1}/{count}")
                
        except Exception as e:
            print_status(f"  ✗ Rate limit test {i+1} error: {e}", Colors.FAIL)
            
        time.sleep(0.1)
    
    print_status(f"✅ Generated {len(violations)} rate limit violations")
    return violations

def manually_update_security_metrics(auth_events, failed_attempts, violations):
    """Manually update security metrics to ensure they're populated"""
    print_status("🔄 Manually updating security metrics...")
    
    try:
        cmd = f'''docker-compose exec -T api python manage.py shell -c "
from jota_news.security_monitoring import (
    SECURITY_EVENTS_TOTAL, AUTHENTICATION_ATTEMPTS_TOTAL,
    FAILED_LOGIN_ATTEMPTS_TOTAL, RATE_LIMIT_VIOLATIONS_TOTAL
)

# Update authentication metrics
AUTHENTICATION_ATTEMPTS_TOTAL.labels(status='success').inc({len([e for e in {auth_events} if e.get('success', False)])})
AUTHENTICATION_ATTEMPTS_TOTAL.labels(status='failure').inc({len([e for e in {auth_events} if not e.get('success', False)])})

# Update failed login attempts
FAILED_LOGIN_ATTEMPTS_TOTAL.labels(username='admin').inc({len([f for f in {failed_attempts} if f.get('username') == 'admin'])})
FAILED_LOGIN_ATTEMPTS_TOTAL.labels(username='root').inc({len([f for f in {failed_attempts} if f.get('username') == 'root'])})
FAILED_LOGIN_ATTEMPTS_TOTAL.labels(username='user').inc({len([f for f in {failed_attempts} if f.get('username') == 'user'])})
FAILED_LOGIN_ATTEMPTS_TOTAL.labels(username='other').inc({len([f for f in {failed_attempts} if f.get('username') not in ['admin', 'root', 'user']])})

# Update rate limit violations
RATE_LIMIT_VIOLATIONS_TOTAL.labels(endpoint='/api/v1/news/articles/').inc({len(violations)})

# Update general security events
SECURITY_EVENTS_TOTAL.labels(event_type='authentication_failure').inc({len(failed_attempts)})
SECURITY_EVENTS_TOTAL.labels(event_type='rate_limit_violation').inc({len(violations)})
SECURITY_EVENTS_TOTAL.labels(event_type='suspicious_activity').inc({random.randint(5, 15)})

print('✓ Security metrics updated manually')
"'''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print_status("✅ Security metrics updated successfully")
        else:
            print_status("⚠ Manual security metrics update failed", Colors.WARNING)
            print_status(f"Error: {result.stderr}", Colors.FAIL)
            
    except Exception as e:
        print_status(f"✗ Error updating security metrics: {e}", Colors.FAIL)

def check_security_metrics():
    """Check if security metrics are now available"""
    print_status("📊 Checking security metrics...")
    
    metrics_to_check = [
        ("jota_authentication_attempts_total", "Authentication Attempts"),
        ("jota_failed_login_attempts_total", "Failed Login Attempts"),
        ("jota_security_events_total", "Security Events"),
        ("jota_rate_limit_violations_total", "Rate Limit Violations"),
    ]
    
    available_metrics = 0
    
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
                    total_value = sum(float(r.get('value', [0, 0])[1]) for r in results)
                    print_status(f"✅ {display_name}: {total_value:.0f}")
                    available_metrics += 1
                else:
                    print_status(f"⚠ {display_name}: No data", Colors.WARNING)
            else:
                print_status(f"❌ {display_name}: Query failed", Colors.FAIL)
                
        except Exception as e:
            print_status(f"❌ {display_name}: Error - {e}", Colors.FAIL)
    
    return available_metrics

def main():
    print_status(f"{Colors.OKCYAN}🔒 Security Events Generator{Colors.ENDC}")
    print_status("=" * 50)
    
    start_time = datetime.now()
    
    # Generate different types of security events
    auth_events = generate_authentication_attempts(50)
    failed_attempts = generate_failed_login_attempts(30)
    violations = generate_rate_limit_violations(25)
    
    # Manually update metrics to ensure they're populated
    manually_update_security_metrics(auth_events, failed_attempts, violations)
    
    # Wait for metrics to be scraped
    print_status("⏳ Waiting for metrics to be scraped...")
    time.sleep(15)
    
    # Check results
    available_metrics = check_security_metrics()
    
    duration = (datetime.now() - start_time).total_seconds()
    
    print_status(f"\n{Colors.OKGREEN}{'='*50}")
    print_status(f"✅ SECURITY EVENTS GENERATION COMPLETED")
    print_status(f"{'='*50}")
    print_status(f"Duration: {duration:.1f} seconds")
    print_status(f"Authentication Events: {len(auth_events)}")
    print_status(f"Failed Login Attempts: {len(failed_attempts)}")
    print_status(f"Rate Limit Violations: {len(violations)}")
    print_status(f"Available Metrics: {available_metrics}/4")
    print_status(f"{'='*50}{Colors.ENDC}")
    
    if available_metrics >= 3:
        print_status("🎉 Security metrics should now be visible in Grafana!")
    else:
        print_status("⚠ Security metrics may need more time to appear", Colors.WARNING)

if __name__ == "__main__":
    main()