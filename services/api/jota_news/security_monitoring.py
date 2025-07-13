"""
Security monitoring and metrics collection for JOTA News System.
"""
import logging
import time
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.auth.models import User
from django.core.cache import cache
from prometheus_client import Counter, Histogram, Gauge, Info
from apps.authentication.models import APIKey
from apps.webhooks.models import WebhookLog

logger = logging.getLogger(__name__)

# Security metrics
SECURITY_EVENTS_TOTAL = Counter(
    'jota_security_events_total',
    'Total number of security events',
    ['event_type', 'severity', 'source']
)

AUTHENTICATION_ATTEMPTS = Counter(
    'jota_authentication_attempts_total',
    'Total authentication attempts',
    ['method', 'result', 'user_type']
)

FAILED_LOGIN_ATTEMPTS = Counter(
    'jota_failed_login_attempts_total',
    'Failed login attempts by IP and user',
    ['ip_address', 'username', 'method']
)

SUSPICIOUS_ACTIVITY = Counter(
    'jota_suspicious_activity_total',
    'Suspicious activity detected',
    ['activity_type', 'severity']
)

API_KEY_USAGE = Counter(
    'jota_api_key_usage_total',
    'API key usage statistics',
    ['key_id', 'endpoint', 'status']
)

WEBHOOK_SECURITY_EVENTS = Counter(
    'jota_webhook_security_events_total',
    'Webhook security events',
    ['source', 'event_type', 'severity']
)

RATE_LIMIT_VIOLATIONS = Counter(
    'jota_rate_limit_violations_total',
    'Rate limit violations',
    ['resource', 'ip_address', 'user_type']
)

ACTIVE_SESSIONS = Gauge(
    'jota_active_sessions',
    'Number of active user sessions'
)

BLOCKED_IPS = Gauge(
    'jota_blocked_ips_total',
    'Number of currently blocked IP addresses'
)

SECURITY_INCIDENTS = Gauge(
    'jota_security_incidents_active',
    'Number of active security incidents',
    ['severity']
)


class SecurityMonitor:
    """Security monitoring and event collection class."""
    
    def __init__(self):
        self.blocked_ips = set()
        self.suspicious_patterns = {}
        self.rate_limit_violations = {}
        self.last_security_scan = timezone.now()
    
    def log_security_event(self, event_type, severity, source, details=None):
        """Log a security event."""
        try:
            SECURITY_EVENTS_TOTAL.labels(
                event_type=event_type,
                severity=severity,
                source=source
            ).inc()
            
            logger.warning(f"Security event: {event_type} (severity: {severity}, source: {source})")
            if details:
                logger.warning(f"Details: {details}")
            
            # Cache recent events for analysis
            cache_key = f"security_events_{event_type}_{int(time.time() // 60)}"
            recent_events = cache.get(cache_key, [])
            recent_events.append({
                'timestamp': timezone.now().isoformat(),
                'severity': severity,
                'source': source,
                'details': details
            })
            cache.set(cache_key, recent_events, timeout=3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
    
    def log_authentication_attempt(self, method, result, user_type, username=None, ip_address=None):
        """Log authentication attempt."""
        try:
            AUTHENTICATION_ATTEMPTS.labels(
                method=method,
                result=result,
                user_type=user_type
            ).inc()
            
            if result == 'failed' and username and ip_address:
                FAILED_LOGIN_ATTEMPTS.labels(
                    ip_address=ip_address,
                    username=username,
                    method=method
                ).inc()
                
                # Check for brute force patterns
                self._check_brute_force_pattern(ip_address, username)
            
        except Exception as e:
            logger.error(f"Error logging authentication attempt: {e}")
    
    def log_api_key_usage(self, key_id, endpoint, status):
        """Log API key usage."""
        try:
            API_KEY_USAGE.labels(
                key_id=key_id,
                endpoint=endpoint,
                status=status
            ).inc()
            
            # Check for suspicious API usage patterns
            if status == 'unauthorized' or status == 'rate_limited':
                self._check_suspicious_api_usage(key_id, endpoint)
            
        except Exception as e:
            logger.error(f"Error logging API key usage: {e}")
    
    def log_webhook_security_event(self, source, event_type, severity, details=None):
        """Log webhook security event."""
        try:
            WEBHOOK_SECURITY_EVENTS.labels(
                source=source,
                event_type=event_type,
                severity=severity
            ).inc()
            
            if severity in ['high', 'critical']:
                self.log_security_event(
                    event_type=f"webhook_{event_type}",
                    severity=severity,
                    source=source,
                    details=details
                )
            
        except Exception as e:
            logger.error(f"Error logging webhook security event: {e}")
    
    def log_rate_limit_violation(self, resource, ip_address, user_type):
        """Log rate limit violation."""
        try:
            RATE_LIMIT_VIOLATIONS.labels(
                resource=resource,
                ip_address=ip_address,
                user_type=user_type
            ).inc()
            
            # Track violations per IP
            violation_key = f"rate_limit_{ip_address}_{int(time.time() // 300)}"  # 5-minute windows
            violations = cache.get(violation_key, 0) + 1
            cache.set(violation_key, violations, timeout=300)
            
            # Block IP if too many violations
            if violations > 10:
                self.block_ip(ip_address, reason="Excessive rate limit violations")
            
        except Exception as e:
            logger.error(f"Error logging rate limit violation: {e}")
    
    def block_ip(self, ip_address, reason):
        """Block an IP address."""
        try:
            self.blocked_ips.add(ip_address)
            BLOCKED_IPS.set(len(self.blocked_ips))
            
            self.log_security_event(
                event_type="ip_blocked",
                severity="medium",
                source="security_monitor",
                details=f"IP {ip_address} blocked: {reason}"
            )
            
            # Store in cache for persistence
            cache.set(f"blocked_ip_{ip_address}", reason, timeout=86400)  # 24 hours
            
        except Exception as e:
            logger.error(f"Error blocking IP: {e}")
    
    def _check_brute_force_pattern(self, ip_address, username):
        """Check for brute force attack patterns."""
        try:
            # Check failed attempts in last 5 minutes
            failed_key = f"failed_attempts_{ip_address}_{username}_{int(time.time() // 300)}"
            failed_attempts = cache.get(failed_key, 0) + 1
            cache.set(failed_key, failed_attempts, timeout=300)
            
            if failed_attempts > 5:
                self.log_security_event(
                    event_type="brute_force_detected",
                    severity="high",
                    source="authentication",
                    details=f"Brute force attack detected from {ip_address} for user {username}"
                )
                
                # Block the IP
                self.block_ip(ip_address, f"Brute force attack against user {username}")
            
        except Exception as e:
            logger.error(f"Error checking brute force pattern: {e}")
    
    def _check_suspicious_api_usage(self, key_id, endpoint):
        """Check for suspicious API usage patterns."""
        try:
            # Track unauthorized attempts per API key
            suspicious_key = f"suspicious_api_{key_id}_{int(time.time() // 300)}"
            attempts = cache.get(suspicious_key, 0) + 1
            cache.set(suspicious_key, attempts, timeout=300)
            
            if attempts > 10:
                SUSPICIOUS_ACTIVITY.labels(
                    activity_type="unauthorized_api_access",
                    severity="medium"
                ).inc()
                
                self.log_security_event(
                    event_type="suspicious_api_usage",
                    severity="medium",
                    source="api_security",
                    details=f"Suspicious API usage detected for key {key_id} on endpoint {endpoint}"
                )
            
        except Exception as e:
            logger.error(f"Error checking suspicious API usage: {e}")
    
    def collect_security_metrics(self):
        """Collect security metrics."""
        try:
            # Count active sessions
            active_sessions = self._count_active_sessions()
            ACTIVE_SESSIONS.set(active_sessions)
            
            # Update blocked IPs count
            BLOCKED_IPS.set(len(self.blocked_ips))
            
            # Analyze webhook security
            self._analyze_webhook_security()
            
            # Check for security incidents
            self._check_security_incidents()
            
            logger.info("Security metrics collected successfully")
            
        except Exception as e:
            logger.error(f"Error collecting security metrics: {e}")
    
    def _count_active_sessions(self):
        """Count active user sessions."""
        try:
            # Users active in last 30 minutes
            active_users = User.objects.filter(
                last_login__gte=timezone.now() - timedelta(minutes=30)
            ).count()
            
            return active_users
        except Exception as e:
            logger.error(f"Error counting active sessions: {e}")
            return 0
    
    def _analyze_webhook_security(self):
        """Analyze webhook security events."""
        try:
            # Check for suspicious webhook patterns
            recent_webhooks = WebhookLog.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=1)
            )
            
            # Group by IP and check for unusual patterns
            ip_counts = {}
            for webhook in recent_webhooks:
                ip = webhook.remote_ip
                ip_counts[ip] = ip_counts.get(ip, 0) + 1
                
                # Check for high frequency from single IP
                if ip_counts[ip] > 100:  # More than 100 requests per hour
                    self.log_webhook_security_event(
                        source=ip,
                        event_type="high_frequency_requests",
                        severity="medium",
                        details=f"High frequency requests from IP {ip}: {ip_counts[ip]} requests/hour"
                    )
            
            # Check for failed webhook attempts
            failed_webhooks = recent_webhooks.filter(status='failed').count()
            if failed_webhooks > 50:  # More than 50 failures per hour
                self.log_webhook_security_event(
                    source="webhook_system",
                    event_type="high_failure_rate",
                    severity="medium",
                    details=f"High webhook failure rate: {failed_webhooks} failures/hour"
                )
            
        except Exception as e:
            logger.error(f"Error analyzing webhook security: {e}")
    
    def _check_security_incidents(self):
        """Check for active security incidents."""
        try:
            # Check cache for recent security events
            current_minute = int(time.time() // 60)
            
            # Check last 5 minutes for incidents
            incident_count = 0
            for i in range(5):
                minute_key = f"security_events_*_{current_minute - i}"
                # This is a simplified check - in production you'd want more sophisticated analysis
                
            # For now, set to 0 as we don't have active incident tracking
            SECURITY_INCIDENTS.labels(severity="low").set(0)
            SECURITY_INCIDENTS.labels(severity="medium").set(0)
            SECURITY_INCIDENTS.labels(severity="high").set(0)
            SECURITY_INCIDENTS.labels(severity="critical").set(0)
            
        except Exception as e:
            logger.error(f"Error checking security incidents: {e}")
    
    def get_security_status(self):
        """Get current security status."""
        try:
            return {
                'blocked_ips': len(self.blocked_ips),
                'active_sessions': self._count_active_sessions(),
                'last_scan': self.last_security_scan.isoformat(),
                'recent_events': self._get_recent_security_events(),
                'threat_level': self._calculate_threat_level()
            }
        except Exception as e:
            logger.error(f"Error getting security status: {e}")
            return {'error': str(e)}
    
    def _get_recent_security_events(self):
        """Get recent security events from cache."""
        try:
            current_minute = int(time.time() // 60)
            events = []
            
            # Get events from last 10 minutes
            for i in range(10):
                minute_key = f"security_events_*_{current_minute - i}"
                # This is simplified - in production you'd iterate through all event types
                
            return events[:10]  # Return last 10 events
        except Exception as e:
            logger.error(f"Error getting recent security events: {e}")
            return []
    
    def _calculate_threat_level(self):
        """Calculate current threat level."""
        try:
            # Simple threat level calculation
            if len(self.blocked_ips) > 10:
                return "high"
            elif len(self.blocked_ips) > 5:
                return "medium"
            elif len(self.blocked_ips) > 0:
                return "low"
            else:
                return "normal"
        except Exception as e:
            logger.error(f"Error calculating threat level: {e}")
            return "unknown"


# Global security monitor instance
security_monitor = SecurityMonitor()


def log_security_event(event_type, severity, source, details=None):
    """Convenient function to log security events."""
    security_monitor.log_security_event(event_type, severity, source, details)


def log_authentication_attempt(method, result, user_type, username=None, ip_address=None):
    """Convenient function to log authentication attempts."""
    security_monitor.log_authentication_attempt(method, result, user_type, username, ip_address)


def log_api_key_usage(key_id, endpoint, status):
    """Convenient function to log API key usage."""
    security_monitor.log_api_key_usage(key_id, endpoint, status)


def get_security_metrics():
    """Get current security metrics."""
    security_monitor.collect_security_metrics()
    return security_monitor.get_security_status()