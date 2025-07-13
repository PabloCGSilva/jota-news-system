"""
Admin configuration for notifications app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    NotificationChannel, NotificationSubscription, NotificationTemplate,
    Notification, NotificationStatistic
)


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    """Admin for NotificationChannel model."""
    list_display = [
        'name', 'channel_type', 'is_active', 'is_default',
        'delivery_rate_display', 'total_sent', 'total_delivered', 'last_used'
    ]
    list_filter = ['channel_type', 'is_active', 'is_default', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = [
        'total_sent', 'total_delivered', 'total_failed', 'delivery_rate',
        'last_used', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'channel_type', 'description', 'is_active', 'is_default')
        }),
        ('Configuration', {
            'fields': ('config', 'rate_limit_per_minute', 'rate_limit_per_hour')
        }),
        ('Statistics', {
            'fields': (
                'total_sent', 'total_delivered', 'total_failed',
                'delivery_rate', 'last_used'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def delivery_rate_display(self, obj):
        """Display delivery rate with color coding."""
        rate = obj.delivery_rate
        if rate >= 95:
            color = 'green'
        elif rate >= 85:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    delivery_rate_display.short_description = 'Delivery Rate'
    
    actions = ['activate_channels', 'deactivate_channels', 'reset_statistics']
    
    def activate_channels(self, request, queryset):
        """Activate selected channels."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} channels activated.')
    activate_channels.short_description = "Activate selected channels"
    
    def deactivate_channels(self, request, queryset):
        """Deactivate selected channels."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} channels deactivated.')
    deactivate_channels.short_description = "Deactivate selected channels"
    
    def reset_statistics(self, request, queryset):
        """Reset statistics for selected channels."""
        updated = queryset.update(
            total_sent=0,
            total_delivered=0,
            total_failed=0,
            last_used=None
        )
        self.message_user(request, f'Statistics reset for {updated} channels.')
    reset_statistics.short_description = "Reset statistics"


@admin.register(NotificationSubscription)
class NotificationSubscriptionAdmin(admin.ModelAdmin):
    """Admin for NotificationSubscription model."""
    list_display = [
        'user', 'channel', 'destination_short', 'min_priority',
        'is_active', 'urgent_only', 'notifications_received', 'last_notification'
    ]
    list_filter = [
        'channel', 'min_priority', 'is_active', 'urgent_only',
        'created_at', 'last_notification'
    ]
    search_fields = ['user__username', 'user__email', 'destination', 'channel__name']
    readonly_fields = ['notifications_received', 'last_notification', 'created_at', 'updated_at']
    filter_horizontal = ['categories']
    
    fieldsets = (
        ('User & Channel', {
            'fields': ('user', 'channel', 'destination')
        }),
        ('Notification Preferences', {
            'fields': ('min_priority', 'urgent_only', 'categories', 'keywords')
        }),
        ('Settings', {
            'fields': ('is_active', 'quiet_hours_start', 'quiet_hours_end')
        }),
        ('Statistics', {
            'fields': ('notifications_received', 'last_notification'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def destination_short(self, obj):
        """Show truncated destination."""
        dest = obj.destination
        return dest[:30] + '...' if len(dest) > 30 else dest
    destination_short.short_description = 'Destination'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('user', 'channel')
    
    actions = ['activate_subscriptions', 'deactivate_subscriptions']
    
    def activate_subscriptions(self, request, queryset):
        """Activate selected subscriptions."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} subscriptions activated.')
    activate_subscriptions.short_description = "Activate selected subscriptions"
    
    def deactivate_subscriptions(self, request, queryset):
        """Deactivate selected subscriptions."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} subscriptions deactivated.')
    deactivate_subscriptions.short_description = "Deactivate selected subscriptions"


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Admin for NotificationTemplate model."""
    list_display = [
        'name', 'template_type', 'channel', 'is_active', 'is_default',
        'times_used', 'last_used'
    ]
    list_filter = ['template_type', 'channel', 'is_active', 'is_default', 'created_at']
    search_fields = ['name', 'subject', 'body_template']
    readonly_fields = ['times_used', 'last_used', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'template_type', 'channel', 'is_active', 'is_default')
        }),
        ('Template Content', {
            'fields': ('subject', 'body_template', 'max_length')
        }),
        ('Usage Statistics', {
            'fields': ('times_used', 'last_used'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('channel')
    
    actions = ['activate_templates', 'deactivate_templates']
    
    def activate_templates(self, request, queryset):
        """Activate selected templates."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} templates activated.')
    activate_templates.short_description = "Activate selected templates"
    
    def deactivate_templates(self, request, queryset):
        """Deactivate selected templates."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} templates deactivated.')
    deactivate_templates.short_description = "Deactivate selected templates"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin for Notification model."""
    list_display = [
        'id_short', 'subscription_user', 'channel_name', 'subject_short',
        'priority', 'status', 'retry_count', 'sent_at', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'subscription__channel', 'created_at',
        'sent_at', 'delivered_at'
    ]
    search_fields = [
        'subject', 'message', 'subscription__user__username',
        'subscription__destination'
    ]
    readonly_fields = [
        'id', 'sent_at', 'delivered_at', 'external_id', 'response_data',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('id', 'subscription', 'news', 'template')
        }),
        ('Content', {
            'fields': ('subject', 'message', 'priority')
        }),
        ('Delivery Information', {
            'fields': (
                'status', 'scheduled_for', 'sent_at', 'delivered_at',
                'external_id', 'response_data'
            )
        }),
        ('Error & Retry', {
            'fields': ('error_message', 'retry_count', 'max_retries'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def id_short(self, obj):
        """Show short ID."""
        return str(obj.id)[:8] + '...'
    id_short.short_description = 'ID'
    
    def subscription_user(self, obj):
        """Show subscription user."""
        return obj.subscription.user.username
    subscription_user.short_description = 'User'
    
    def channel_name(self, obj):
        """Show channel name."""
        return obj.subscription.channel.name
    channel_name.short_description = 'Channel'
    
    def subject_short(self, obj):
        """Show truncated subject."""
        subject = obj.subject
        return subject[:50] + '...' if len(subject) > 50 else subject
    subject_short.short_description = 'Subject'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'subscription__user', 'subscription__channel', 'news', 'template'
        )
    
    def has_add_permission(self, request):
        """Notifications are created automatically."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Limited editing allowed."""
        return request.user.is_superuser
    
    actions = ['retry_failed_notifications', 'cancel_pending_notifications']
    
    def retry_failed_notifications(self, request, queryset):
        """Retry failed notifications."""
        from .tasks import send_notification_task
        
        failed_notifications = queryset.filter(status='failed')
        count = 0
        
        for notification in failed_notifications:
            if notification.retry_count < notification.max_retries:
                notification.status = 'pending'
                notification.error_message = ''
                notification.save()
                send_notification_task.delay(notification.id)
                count += 1
        
        self.message_user(request, f'{count} failed notifications queued for retry.')
    retry_failed_notifications.short_description = "Retry failed notifications"
    
    def cancel_pending_notifications(self, request, queryset):
        """Cancel pending notifications."""
        updated = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f'{updated} pending notifications cancelled.')
    cancel_pending_notifications.short_description = "Cancel pending notifications"


@admin.register(NotificationStatistic)
class NotificationStatisticAdmin(admin.ModelAdmin):
    """Admin for NotificationStatistic model."""
    list_display = [
        'date', 'channel', 'total_sent', 'total_delivered',
        'delivery_rate_display', 'avg_delivery_time'
    ]
    list_filter = ['date', 'channel', 'created_at']
    search_fields = ['channel__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def delivery_rate_display(self, obj):
        """Display delivery rate with color coding."""
        rate = obj.delivery_rate
        if rate >= 95:
            color = 'green'
        elif rate >= 85:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    delivery_rate_display.short_description = 'Delivery Rate'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('channel')
    
    def has_add_permission(self, request):
        """Statistics are generated automatically."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Statistics are read-only."""
        return False