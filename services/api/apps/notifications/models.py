"""
Models for notifications app.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import RegexValidator
import uuid
import json


class NotificationChannel(models.Model):
    """
    Notification channels (Email, SMS, Push, Webhook, Slack).
    """
    CHANNEL_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('webhook', 'Webhook'),
        ('slack', 'Slack'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES)
    description = models.TextField(blank=True)
    
    # Configuration
    config = models.JSONField(
        default=dict,
        help_text="Channel-specific configuration"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # Rate limiting
    rate_limit_per_minute = models.IntegerField(default=60)
    rate_limit_per_hour = models.IntegerField(default=1000)
    
    # Statistics
    total_sent = models.BigIntegerField(default=0)
    total_delivered = models.BigIntegerField(default=0)
    total_failed = models.BigIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_channel'
        verbose_name = 'Notification Channel'
        verbose_name_plural = 'Notification Channels'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"
    
    def increment_sent(self):
        """Increment sent counter."""
        self.total_sent += 1
        self.last_used = timezone.now()
        self.save(update_fields=['total_sent', 'last_used'])
    
    def increment_delivered(self):
        """Increment delivered counter."""
        self.total_delivered += 1
        self.save(update_fields=['total_delivered'])
    
    def increment_failed(self):
        """Increment failed counter."""
        self.total_failed += 1
        self.save(update_fields=['total_failed'])
    
    @property
    def delivery_rate(self):
        """Calculate delivery rate percentage."""
        if self.total_sent == 0:
            return 0
        return round((self.total_delivered / self.total_sent) * 100, 2)


class NotificationSubscription(models.Model):
    """
    User subscriptions to notification channels.
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='notification_subscriptions')
    channel = models.ForeignKey(NotificationChannel, on_delete=models.CASCADE, related_name='subscriptions')
    
    # Subscription details
    destination = models.CharField(
        max_length=255,
        help_text="Phone number, email, webhook URL, etc."
    )
    min_priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text="Minimum priority level to receive notifications"
    )
    
    # Filters
    categories = models.ManyToManyField(
        'news.Category',
        blank=True,
        help_text="Only receive notifications for these categories"
    )
    keywords = models.JSONField(
        default=list,
        help_text="Keywords to filter notifications"
    )
    
    # Settings
    is_active = models.BooleanField(default=True)
    urgent_only = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    # Statistics
    notifications_received = models.PositiveIntegerField(default=0)
    last_notification = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_subscription'
        verbose_name = 'Notification Subscription'
        verbose_name_plural = 'Notification Subscriptions'
        unique_together = ['user', 'channel', 'destination']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} -> {self.channel.name} ({self.destination})"
    
    def increment_notifications(self):
        """Increment notifications received counter."""
        self.notifications_received += 1
        self.last_notification = timezone.now()
        self.save(update_fields=['notifications_received', 'last_notification'])


class NotificationTemplate(models.Model):
    """
    Templates for different types of notifications.
    """
    TEMPLATE_TYPES = [
        ('urgent_news', 'Urgent News'),
        ('daily_summary', 'Daily Summary'),
        ('weekly_digest', 'Weekly Digest'),
        ('breaking_news', 'Breaking News'),
        ('category_alert', 'Category Alert'),
        ('custom', 'Custom'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    channel = models.ForeignKey(NotificationChannel, on_delete=models.CASCADE, related_name='templates')
    
    # Template content
    subject = models.CharField(max_length=255, blank=True)
    body_template = models.TextField(
        help_text="Template with placeholders like {{title}}, {{content}}, {{url}}"
    )
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    max_length = models.IntegerField(null=True, blank=True)
    
    # Usage statistics
    times_used = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_template'
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
        unique_together = ['channel', 'template_type', 'is_default']
        ordering = ['channel', 'template_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.channel.name})"
    
    def render(self, context):
        """Render template with context."""
        import re
        
        rendered_subject = self.subject
        rendered_body = self.body_template
        
        # Simple template rendering
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            rendered_subject = rendered_subject.replace(placeholder, str(value))
            rendered_body = rendered_body.replace(placeholder, str(value))
        
        # Truncate if max_length is set
        if self.max_length and len(rendered_body) > self.max_length:
            rendered_body = rendered_body[:self.max_length - 3] + '...'
        
        return rendered_subject, rendered_body
    
    def increment_usage(self):
        """Increment usage counter."""
        self.times_used += 1
        self.last_used = timezone.now()
        self.save(update_fields=['times_used', 'last_used'])


class Notification(models.Model):
    """
    Individual notification instances.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Recipients
    subscription = models.ForeignKey(
        NotificationSubscription,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Content
    news = models.ForeignKey(
        'news.News',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Message details
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Delivery details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scheduled_for = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Response details
    external_id = models.CharField(max_length=255, blank=True)
    response_data = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    
    # Retry information
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    
    # Metadata
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['subscription', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['scheduled_for']),
        ]
    
    def __str__(self):
        return f"Notification to {self.subscription.destination} - {self.status}"
    
    def mark_sent(self, external_id=None, response_data=None):
        """Mark notification as sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        if external_id:
            self.external_id = external_id
        if response_data:
            self.response_data = response_data
        self.save()
        
        # Update channel statistics
        self.subscription.channel.increment_sent()
        self.subscription.increment_notifications()
    
    def mark_delivered(self, response_data=None):
        """Mark notification as delivered."""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        if response_data:
            self.response_data.update(response_data)
        self.save()
        
        # Update channel statistics
        self.subscription.channel.increment_delivered()
    
    def mark_failed(self, error_message, retry=True):
        """Mark notification as failed."""
        self.error_message = error_message
        
        if retry and self.retry_count < self.max_retries:
            self.retry_count += 1
            self.status = 'pending'
            # Schedule retry with exponential backoff
            from datetime import timedelta
            retry_delay = timedelta(minutes=2 ** self.retry_count)
            self.scheduled_for = timezone.now() + retry_delay
        else:
            self.status = 'failed'
            # Update channel statistics
            self.subscription.channel.increment_failed()
        
        self.save()
    
    def can_send_now(self):
        """Check if notification can be sent now considering quiet hours."""
        if not self.subscription.quiet_hours_start or not self.subscription.quiet_hours_end:
            return True
        
        now = timezone.now().time()
        start = self.subscription.quiet_hours_start
        end = self.subscription.quiet_hours_end
        
        # Handle quiet hours that cross midnight
        if start <= end:
            return not (start <= now <= end)
        else:
            return end <= now <= start


class NotificationStatistic(models.Model):
    """
    Daily notification statistics.
    """
    date = models.DateField()
    channel = models.ForeignKey(NotificationChannel, on_delete=models.CASCADE)
    
    # Counts
    total_sent = models.PositiveIntegerField(default=0)
    total_delivered = models.PositiveIntegerField(default=0)
    total_failed = models.PositiveIntegerField(default=0)
    total_cancelled = models.PositiveIntegerField(default=0)
    
    # Priority breakdown
    urgent_notifications = models.PositiveIntegerField(default=0)
    high_notifications = models.PositiveIntegerField(default=0)
    medium_notifications = models.PositiveIntegerField(default=0)
    low_notifications = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    avg_delivery_time = models.FloatField(default=0.0)  # in seconds
    delivery_rate = models.FloatField(default=0.0)  # percentage
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_statistic'
        verbose_name = 'Notification Statistic'
        verbose_name_plural = 'Notification Statistics'
        unique_together = ['date', 'channel']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.channel.name} - {self.date}"