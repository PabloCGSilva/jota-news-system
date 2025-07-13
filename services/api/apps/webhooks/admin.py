"""
Admin configuration for webhook app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import WebhookSource, WebhookLog, WebhookRetry, WebhookStatistic


@admin.register(WebhookSource)
class WebhookSourceAdmin(admin.ModelAdmin):
    """Admin for WebhookSource model."""
    list_display = [
        'name', 'endpoint_url', 'is_active', 'success_rate_display',
        'total_requests', 'last_request_at', 'created_at'
    ]
    list_filter = ['is_active', 'requires_authentication', 'created_at']
    search_fields = ['name', 'description', 'endpoint_url']
    readonly_fields = [
        'total_requests', 'successful_requests', 'failed_requests',
        'success_rate', 'last_request_at', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'endpoint_url', 'is_active')
        }),
        ('Configuration', {
            'fields': (
                'secret_key', 'expected_content_type', 'requires_authentication',
                'rate_limit_per_minute'
            )
        }),
        ('Statistics', {
            'fields': (
                'total_requests', 'successful_requests', 'failed_requests',
                'success_rate', 'last_request_at'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def success_rate_display(self, obj):
        """Display success rate with color coding."""
        rate = obj.success_rate
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
    success_rate_display.short_description = 'Success Rate'
    
    actions = ['activate_sources', 'deactivate_sources', 'reset_statistics']
    
    def activate_sources(self, request, queryset):
        """Activate selected webhook sources."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} webhook sources activated.')
    activate_sources.short_description = "Activate selected sources"
    
    def deactivate_sources(self, request, queryset):
        """Deactivate selected webhook sources."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} webhook sources deactivated.')
    deactivate_sources.short_description = "Deactivate selected sources"
    
    def reset_statistics(self, request, queryset):
        """Reset statistics for selected sources."""
        updated = queryset.update(
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            last_request_at=None
        )
        self.message_user(request, f'Statistics reset for {updated} sources.')
    reset_statistics.short_description = "Reset statistics"


class WebhookRetryInline(admin.TabularInline):
    """Inline admin for webhook retries."""
    model = WebhookRetry
    extra = 0
    readonly_fields = ['created_at']
    fields = ['attempt_number', 'error_message', 'next_retry_at', 'created_at']


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    """Admin for WebhookLog model."""
    list_display = [
        'source', 'method', 'status', 'status_code', 'processing_time',
        'remote_ip', 'created_at'
    ]
    list_filter = ['source', 'status', 'method', 'status_code', 'created_at']
    search_fields = ['source__name', 'path', 'error_message', 'remote_ip']
    readonly_fields = [
        'id', 'method', 'path', 'headers', 'query_params', 'body',
        'status_code', 'response_data', 'processing_time', 'created_news_id',
        'user_agent', 'remote_ip', 'correlation_id', 'created_at', 'updated_at'
    ]
    inlines = [WebhookRetryInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Request Information', {
            'fields': ('source', 'method', 'path', 'remote_ip', 'user_agent')
        }),
        ('Request Data', {
            'fields': ('headers', 'query_params', 'body'),
            'classes': ('collapse',)
        }),
        ('Response Information', {
            'fields': ('status', 'status_code', 'response_data', 'error_message')
        }),
        ('Processing Details', {
            'fields': ('processing_time', 'created_news_id', 'correlation_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('source')
    
    def has_add_permission(self, request):
        """Logs are created automatically."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Logs are mostly read-only."""
        return request.user.is_superuser
    
    actions = ['retry_failed_webhooks', 'mark_as_processed']
    
    def retry_failed_webhooks(self, request, queryset):
        """Retry failed webhooks."""
        from .tasks import process_webhook_async
        
        failed_logs = queryset.filter(status='failed')
        count = 0
        
        for log in failed_logs:
            log.status = 'pending'
            log.save()
            process_webhook_async.delay(log.id)
            count += 1
        
        self.message_user(request, f'{count} failed webhooks queued for retry.')
    retry_failed_webhooks.short_description = "Retry failed webhooks"
    
    def mark_as_processed(self, request, queryset):
        """Mark webhooks as processed."""
        updated = queryset.update(status='success')
        self.message_user(request, f'{updated} webhooks marked as processed.')
    mark_as_processed.short_description = "Mark as processed"


@admin.register(WebhookRetry)
class WebhookRetryAdmin(admin.ModelAdmin):
    """Admin for WebhookRetry model."""
    list_display = [
        'webhook_log', 'attempt_number', 'error_message_short',
        'next_retry_at', 'created_at'
    ]
    list_filter = ['attempt_number', 'created_at']
    search_fields = ['webhook_log__source__name', 'error_message']
    readonly_fields = ['created_at']
    
    def error_message_short(self, obj):
        """Show truncated error message."""
        return obj.error_message[:100] + '...' if len(obj.error_message) > 100 else obj.error_message
    error_message_short.short_description = 'Error Message'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('webhook_log__source')
    
    def has_add_permission(self, request):
        """Retries are created automatically."""
        return False


@admin.register(WebhookStatistic)
class WebhookStatisticAdmin(admin.ModelAdmin):
    """Admin for WebhookStatistic model."""
    list_display = [
        'source', 'date', 'total_requests', 'successful_requests',
        'failed_requests', 'success_rate_display', 'news_created'
    ]
    list_filter = ['source', 'date', 'created_at']
    search_fields = ['source__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def success_rate_display(self, obj):
        """Display success rate with color coding."""
        rate = obj.success_rate
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
    success_rate_display.short_description = 'Success Rate'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('source')
    
    def has_add_permission(self, request):
        """Statistics are generated automatically."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Statistics are read-only."""
        return False