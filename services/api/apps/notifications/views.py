"""
Views for notifications app.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Avg, Sum
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import (
    NotificationChannel, NotificationSubscription, NotificationTemplate,
    Notification, NotificationStatistic
)
from .serializers import (
    NotificationChannelSerializer, NotificationSubscriptionSerializer,
    NotificationTemplateSerializer, NotificationSerializer,
    NotificationStatisticSerializer, SendNotificationSerializer,
    BulkSubscriptionSerializer, NotificationStatsSerializer,
    TestNotificationSerializer, TemplateTestSerializer
)
from .tasks import (
    send_notification_task, send_urgent_notification, send_daily_summary,
    process_pending_notifications
)
from .providers import send_notification

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="List notification channels",
        description="Get a list of all notification channels and their configurations."
    ),
    create=extend_schema(
        summary="Create notification channel",
        description="Create a new notification channel for sending notifications."
    ),
    retrieve=extend_schema(
        summary="Get notification channel details",
        description="Get detailed information about a specific notification channel."
    ),
    update=extend_schema(
        summary="Update notification channel",
        description="Update an existing notification channel configuration."
    ),
)
class NotificationChannelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification channels.
    """
    queryset = NotificationChannel.objects.all()
    serializer_class = NotificationChannelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['channel_type', 'is_active', 'is_default']
    ordering = ['name']
    
    @extend_schema(
        summary="Test notification channel",
        description="Send a test notification through the channel."
    )
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test notification channel."""
        channel = self.get_object()
        serializer = TestNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Send test notification
        success, external_id, response_data = send_notification(
            channel_type=channel.channel_type,
            config=channel.config,
            destination=serializer.validated_data['destination'],
            subject=serializer.validated_data.get('subject', 'Test Notification'),
            message=serializer.validated_data['message'],
            metadata={'test': True, 'user': request.user.username}
        )
        
        if success:
            return Response({
                'success': True,
                'external_id': external_id,
                'response_data': response_data
            })
        else:
            return Response({
                'success': False,
                'error': response_data.get('error', 'Unknown error'),
                'response_data': response_data
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get channel statistics",
        description="Get detailed statistics for a notification channel."
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get channel statistics."""
        channel = self.get_object()
        
        # Get recent statistics
        recent_stats = NotificationStatistic.objects.filter(
            channel=channel,
            date__gte=timezone.now().date() - timezone.timedelta(days=30)
        ).order_by('-date')
        
        # Calculate aggregated metrics
        total_stats = recent_stats.aggregate(
            total_sent=Sum('total_sent'),
            total_delivered=Sum('total_delivered'),
            total_failed=Sum('total_failed'),
            avg_delivery_time=Avg('avg_delivery_time')
        )
        
        return Response({
            'channel': NotificationChannelSerializer(channel).data,
            'recent_statistics': NotificationStatisticSerializer(recent_stats, many=True).data,
            'summary': {
                'total_sent': total_stats['total_sent'] or 0,
                'total_delivered': total_stats['total_delivered'] or 0,
                'total_failed': total_stats['total_failed'] or 0,
                'delivery_rate': (total_stats['total_delivered'] or 0) / max(total_stats['total_sent'] or 1, 1) * 100,
                'avg_delivery_time': total_stats['avg_delivery_time'] or 0
            }
        })


@extend_schema_view(
    list=extend_schema(
        summary="List notification subscriptions",
        description="Get a list of notification subscriptions for the current user or all users (if staff)."
    ),
    create=extend_schema(
        summary="Create notification subscription",
        description="Create a new notification subscription."
    ),
)
class NotificationSubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification subscriptions.
    """
    serializer_class = NotificationSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['channel', 'is_active', 'urgent_only', 'min_priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get subscriptions for current user or all if staff."""
        if self.request.user.is_staff:
            return NotificationSubscription.objects.all().select_related(
                'user', 'channel'
            ).prefetch_related('categories')
        else:
            return NotificationSubscription.objects.filter(
                user=self.request.user
            ).select_related('channel').prefetch_related('categories')
    
    def perform_create(self, serializer):
        """Set current user if not provided."""
        if not serializer.validated_data.get('user'):
            serializer.save(user=self.request.user)
        else:
            serializer.save()
    
    @extend_schema(
        summary="Bulk create subscriptions",
        description="Create multiple subscriptions at once."
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple subscriptions."""
        serializer = BulkSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from django.contrib.auth.models import User
        from apps.news.models import Category
        
        user_ids = serializer.validated_data['user_ids']
        channel_id = serializer.validated_data['channel_id']
        destinations = serializer.validated_data.get('destinations', [])
        min_priority = serializer.validated_data['min_priority']
        category_ids = serializer.validated_data.get('categories', [])
        
        # Get objects
        users = User.objects.filter(id__in=user_ids)
        channel = NotificationChannel.objects.get(id=channel_id)
        categories = Category.objects.filter(id__in=category_ids) if category_ids else []
        
        created_subscriptions = []
        
        for i, user in enumerate(users):
            destination = destinations[i] if destinations else f"{user.email}"
            
            subscription, created = NotificationSubscription.objects.get_or_create(
                user=user,
                channel=channel,
                destination=destination,
                defaults={
                    'min_priority': min_priority,
                    'is_active': True
                }
            )
            
            if categories:
                subscription.categories.set(categories)
            
            if created:
                created_subscriptions.append(subscription)
        
        return Response({
            'created_count': len(created_subscriptions),
            'total_users': len(users),
            'subscriptions': NotificationSubscriptionSerializer(created_subscriptions, many=True).data
        })


@extend_schema_view(
    list=extend_schema(
        summary="List notification templates",
        description="Get a list of notification templates."
    ),
    create=extend_schema(
        summary="Create notification template",
        description="Create a new notification template."
    ),
)
class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification templates.
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['channel', 'template_type', 'is_active', 'is_default']
    ordering = ['channel', 'template_type', 'name']
    
    def get_queryset(self):
        """Optimize queryset."""
        return super().get_queryset().select_related('channel')
    
    @extend_schema(
        summary="Test template",
        description="Test template rendering with sample context."
    )
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test template rendering."""
        template = self.get_object()
        serializer = TemplateTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        context = serializer.validated_data['context']
        
        try:
            subject, message = template.render(context)
            return Response({
                'subject': subject,
                'message': message,
                'context': context
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(
        summary="List notifications",
        description="Get a list of notifications with filtering options."
    ),
    retrieve=extend_schema(
        summary="Get notification details",
        description="Get detailed information about a specific notification."
    ),
)
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'priority', 'subscription__channel']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get notifications for current user or all if staff."""
        queryset = Notification.objects.select_related(
            'subscription__user', 'subscription__channel', 'news', 'template'
        )
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(subscription__user=self.request.user)
        
        return queryset
    
    @extend_schema(
        summary="Retry failed notification",
        description="Retry sending a failed notification."
    )
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry failed notification."""
        notification = self.get_object()
        
        if notification.status != 'failed':
            return Response(
                {'error': 'Only failed notifications can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if notification.retry_count >= notification.max_retries:
            return Response(
                {'error': 'Maximum retries exceeded'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset notification
        notification.status = 'pending'
        notification.scheduled_for = timezone.now()
        notification.error_message = ''
        notification.save()
        
        # Send notification
        send_notification_task.delay(notification.id)
        
        return Response({'message': 'Notification retry initiated'})
    
    @extend_schema(
        summary="Cancel pending notification",
        description="Cancel a pending notification."
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel pending notification."""
        notification = self.get_object()
        
        if notification.status not in ['pending', 'sending']:
            return Response(
                {'error': 'Only pending or sending notifications can be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notification.status = 'cancelled'
        notification.save()
        
        return Response({'message': 'Notification cancelled'})


@extend_schema_view(
    list=extend_schema(
        summary="List notification statistics",
        description="Get notification statistics by date and channel."
    ),
)
class NotificationStatisticViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing notification statistics.
    """
    queryset = NotificationStatistic.objects.all()
    serializer_class = NotificationStatisticSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['date', 'channel']
    ordering = ['-date']
    
    def get_queryset(self):
        """Optimize queryset."""
        return super().get_queryset().select_related('channel')


class NotificationAPIViewSet(viewsets.ViewSet):
    """
    API endpoints for notification operations.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Send manual notification",
        description="Send notification to specific subscriptions."
    )
    @action(detail=False, methods=['post'])
    def send(self, request):
        """Send manual notification."""
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        subscription_ids = serializer.validated_data['subscription_ids']
        subject = serializer.validated_data.get('subject', '')
        message = serializer.validated_data['message']
        priority = serializer.validated_data['priority']
        scheduled_for = serializer.validated_data.get('scheduled_for', timezone.now())
        
        # Get subscriptions
        subscriptions = NotificationSubscription.objects.filter(
            id__in=subscription_ids,
            is_active=True
        )
        
        notifications_created = 0
        
        for subscription in subscriptions:
            notification = Notification.objects.create(
                subscription=subscription,
                subject=subject,
                message=message,
                priority=priority,
                scheduled_for=scheduled_for,
                metadata={
                    'manual_send': True,
                    'sent_by': request.user.username
                }
            )
            
            # Send immediately or schedule
            if scheduled_for <= timezone.now():
                send_notification_task.delay(notification.id)
            else:
                send_notification_task.apply_async(args=[notification.id], eta=scheduled_for)
            
            notifications_created += 1
        
        return Response({
            'message': f'{notifications_created} notifications created',
            'notifications_created': notifications_created,
            'scheduled_for': scheduled_for
        })
    
    @extend_schema(
        summary="Send urgent news notification",
        description="Send urgent notification for a specific news article."
    )
    @action(detail=False, methods=['post'])
    def urgent(self, request):
        """Send urgent news notification."""
        news_id = request.data.get('news_id')
        
        if not news_id:
            return Response(
                {'error': 'news_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify news exists and is urgent
        from apps.news.models import News
        try:
            news = News.objects.get(id=news_id)
            if not news.is_urgent:
                return Response(
                    {'error': 'News is not marked as urgent'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except News.DoesNotExist:
            return Response(
                {'error': 'News not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Send urgent notification
        task = send_urgent_notification.delay(news_id)
        
        return Response({
            'message': 'Urgent notification task started',
            'task_id': task.id,
            'news_id': str(news_id)
        })
    
    @extend_schema(
        summary="Get notification dashboard",
        description="Get aggregated notification statistics for dashboard."
    )
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get notification dashboard data."""
        # Get date range
        serializer = NotificationStatsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        date_from = serializer.validated_data.get('date_from', timezone.now().date() - timezone.timedelta(days=7))
        date_to = serializer.validated_data.get('date_to', timezone.now().date())
        channel_id = serializer.validated_data.get('channel_id')
        
        # Base queryset
        stats_queryset = NotificationStatistic.objects.filter(
            date__range=[date_from, date_to]
        )
        
        if channel_id:
            stats_queryset = stats_queryset.filter(channel_id=channel_id)
        
        # Aggregate statistics
        total_stats = stats_queryset.aggregate(
            total_sent=Sum('total_sent'),
            total_delivered=Sum('total_delivered'),
            total_failed=Sum('total_failed'),
            avg_delivery_time=Avg('avg_delivery_time')
        )
        
        # Channel breakdown
        channel_stats = stats_queryset.values('channel__name').annotate(
            total_sent=Sum('total_sent'),
            total_delivered=Sum('total_delivered'),
            total_failed=Sum('total_failed')
        ).order_by('-total_sent')
        
        # Priority breakdown
        priority_stats = stats_queryset.aggregate(
            urgent=Sum('urgent_notifications'),
            high=Sum('high_notifications'),
            medium=Sum('medium_notifications'),
            low=Sum('low_notifications')
        )
        
        # Recent activity
        recent_notifications = Notification.objects.filter(
            created_at__date__range=[date_from, date_to]
        ).order_by('-created_at')[:10]
        
        if not request.user.is_staff:
            recent_notifications = recent_notifications.filter(
                subscription__user=request.user
            )
        
        # Active channels and subscriptions
        active_channels = NotificationChannel.objects.filter(is_active=True).count()
        total_subscriptions = NotificationSubscription.objects.filter(is_active=True).count()
        
        return Response({
            'date_range': {'from': date_from, 'to': date_to},
            'overview': {
                'total_sent': total_stats['total_sent'] or 0,
                'total_delivered': total_stats['total_delivered'] or 0,
                'total_failed': total_stats['total_failed'] or 0,
                'delivery_rate': (total_stats['total_delivered'] or 0) / max(total_stats['total_sent'] or 1, 1) * 100,
                'avg_delivery_time': total_stats['avg_delivery_time'] or 0,
                'active_channels': active_channels,
                'total_subscriptions': total_subscriptions
            },
            'channel_breakdown': list(channel_stats),
            'priority_breakdown': priority_stats,
            'recent_activity': NotificationSerializer(recent_notifications, many=True).data,
            'daily_stats': NotificationStatisticSerializer(stats_queryset.order_by('-date'), many=True).data
        })
    
    @extend_schema(
        summary="Trigger daily summary",
        description="Manually trigger daily summary notifications."
    )
    @action(detail=False, methods=['post'])
    def daily_summary(self, request):
        """Trigger daily summary."""
        task = send_daily_summary.delay()
        
        return Response({
            'message': 'Daily summary task started',
            'task_id': task.id
        })
    
    @extend_schema(
        summary="Process pending notifications",
        description="Manually trigger processing of pending notifications."
    )
    @action(detail=False, methods=['post'])
    def process_pending(self, request):
        """Process pending notifications."""
        task = process_pending_notifications.delay()
        
        return Response({
            'message': 'Pending notifications processing started',
            'task_id': task.id
        })