"""
Utility functions for webhook app.
"""
import hashlib
import hmac
import time
import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """
    Get client IP address from request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def verify_webhook_signature(request, secret_key):
    """
    Verify webhook signature using HMAC.
    """
    try:
        # Get signature from header
        signature = request.headers.get('X-Hub-Signature-256') or request.headers.get('X-Signature')
        
        if not signature:
            return False
        
        # Remove 'sha256=' prefix if present
        if signature.startswith('sha256='):
            signature = signature[7:]
        
        # Calculate expected signature
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            request.body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        return False


def rate_limit_check(source, client_ip):
    """
    Check if client has exceeded rate limit for webhook source.
    """
    try:
        # Create cache key
        cache_key = f"webhook_rate_limit:{source.id}:{client_ip}"
        
        # Get current request count
        current_count = cache.get(cache_key, 0)
        
        # Check if limit exceeded
        if current_count >= source.rate_limit_per_minute:
            return False
        
        # Increment counter
        cache.set(cache_key, current_count + 1, 60)  # 1 minute TTL
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking rate limit: {str(e)}")
        return True  # Allow request on error


def validate_webhook_data(data, source):
    """
    Validate webhook data against source configuration.
    """
    errors = []
    
    # Required fields
    required_fields = ['title', 'content', 'source']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")
    
    # Field length validation
    if 'title' in data and len(data['title']) > 200:
        errors.append("Title exceeds maximum length of 200 characters")
    
    if 'content' in data and len(data['content']) > 10000:
        errors.append("Content exceeds maximum length of 10000 characters")
    
    # URL validation
    if 'source_url' in data and data['source_url']:
        import validators
        if not validators.url(data['source_url']):
            errors.append("Invalid source URL format")
    
    # Date validation
    if 'published_at' in data and data['published_at']:
        try:
            from datetime import datetime
            from django.utils import timezone
            
            if isinstance(data['published_at'], str):
                # Try to parse ISO format
                pub_date = datetime.fromisoformat(data['published_at'].replace('Z', '+00:00'))
            else:
                pub_date = data['published_at']
            
            # Check if date is not in future
            if pub_date > timezone.now():
                errors.append("Published date cannot be in the future")
                
        except (ValueError, TypeError):
            errors.append("Invalid published_at date format")
    
    return errors


def extract_category_hints(data):
    """
    Extract category hints from webhook data.
    """
    hints = {}
    
    # Direct category hints
    if 'category_hint' in data:
        hints['category'] = data['category_hint']
    
    if 'subcategory_hint' in data:
        hints['subcategory'] = data['subcategory_hint']
    
    # Extract from metadata
    if 'metadata' in data and isinstance(data['metadata'], dict):
        if 'category' in data['metadata']:
            hints['category'] = data['metadata']['category']
        
        if 'subcategory' in data['metadata']:
            hints['subcategory'] = data['metadata']['subcategory']
    
    # Extract from tags
    if 'tags' in data and isinstance(data['tags'], list):
        # Look for category-like tags
        category_keywords = ['poder', 'tributos', 'saude', 'trabalhista']
        for tag in data['tags']:
            if tag.lower() in category_keywords:
                hints['category'] = tag.lower()
                break
    
    return hints


def prepare_news_data(webhook_data, source):
    """
    Prepare news data from webhook for database insertion.
    """
    from django.utils import timezone
    
    # Basic news data
    news_data = {
        'title': webhook_data.get('title', '').strip(),
        'content': webhook_data.get('content', '').strip(),
        'summary': webhook_data.get('summary', '').strip(),
        'source': webhook_data.get('source', source.name),
        'source_url': webhook_data.get('source_url', ''),
        'author': webhook_data.get('author', ''),
        'external_id': webhook_data.get('external_id', ''),
        'is_urgent': webhook_data.get('is_urgent', False),
        'is_published': True,  # Default to published
        'published_at': timezone.now()
    }
    
    # Parse published_at if provided
    if webhook_data.get('published_at'):
        try:
            from datetime import datetime
            if isinstance(webhook_data['published_at'], str):
                news_data['published_at'] = datetime.fromisoformat(
                    webhook_data['published_at'].replace('Z', '+00:00')
                )
            else:
                news_data['published_at'] = webhook_data['published_at']
        except (ValueError, TypeError):
            # Use current time if parsing fails
            pass
    
    # Handle priority mapping
    priority_urgency_map = {
        'urgent': True,
        'high': True,
        'medium': False,
        'low': False
    }
    
    if webhook_data.get('priority') in priority_urgency_map:
        news_data['is_urgent'] = priority_urgency_map[webhook_data['priority']]
    
    return news_data


def create_processing_log(news, stage, status, message="", processing_time=0.0):
    """
    Create a processing log entry for news.
    """
    from apps.news.models import NewsProcessingLog
    
    return NewsProcessingLog.objects.create(
        news=news,
        stage=stage,
        status=status,
        message=message,
        processing_time=processing_time
    )


def send_webhook_notification(webhook_log, news=None):
    """
    Send notification about webhook processing (if configured).
    """
    try:
        # This could be extended to send notifications to Slack, email, etc.
        # For now, just log the event
        
        if news:
            logger.info(
                f"Webhook processed successfully: {webhook_log.source.name} created news '{news.title}'"
            )
        else:
            logger.warning(
                f"Webhook processing failed: {webhook_log.source.name} - {webhook_log.error_message}"
            )
            
    except Exception as e:
        logger.error(f"Error sending webhook notification: {str(e)}")


def cleanup_old_webhook_logs(days=30):
    """
    Clean up old webhook logs.
    """
    from django.utils import timezone
    from .models import WebhookLog
    
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count = WebhookLog.objects.filter(created_at__lt=cutoff_date).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old webhook logs")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error cleaning up webhook logs: {str(e)}")
        return 0


def generate_webhook_signature(payload, secret_key):
    """
    Generate webhook signature for testing purposes.
    """
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={signature}"