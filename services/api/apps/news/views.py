"""
Views for news app.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes

from .models import Category, Subcategory, Tag, News, NewsProcessingLog, NewsStatistic
from .serializers import (
    CategorySerializer, SubcategorySerializer, TagSerializer,
    NewsListSerializer, NewsDetailSerializer, NewsCreateSerializer,
    NewsUpdateSerializer, NewsProcessingLogSerializer, NewsStatisticSerializer,
    NewsSearchSerializer
)
from .filters import NewsFilter
from .pagination import NewsPagination


@extend_schema_view(
    list=extend_schema(
        summary="List all categories",
        description="Get a list of all news categories with their statistics."
    ),
    create=extend_schema(
        summary="Create a new category",
        description="Create a new news category."
    ),
    retrieve=extend_schema(
        summary="Get category details",
        description="Get detailed information about a specific category."
    ),
    update=extend_schema(
        summary="Update category",
        description="Update an existing category."
    ),
    destroy=extend_schema(
        summary="Delete category",
        description="Delete a category (only if no news are associated)."
    ),
)
class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing news categories.
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['is_active']
    
    def get_queryset(self):
        """Get queryset with optional inactive categories for staff."""
        if self.request.user.is_staff:
            return Category.objects.all()
        return Category.objects.filter(is_active=True)
    
    @extend_schema(
        summary="Get category statistics",
        description="Get detailed statistics for a category."
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get category statistics."""
        category = self.get_object()
        
        # Get statistics from cache or calculate
        cache_key = f"category_stats_{category.id}"
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = {
                'total_news': category.news.filter(is_published=True).count(),
                'urgent_news': category.news.filter(is_published=True, is_urgent=True).count(),
                'subcategories': category.subcategories.filter(is_active=True).count(),
                'recent_news': category.news.filter(
                    is_published=True,
                    published_at__gte=timezone.now() - timezone.timedelta(days=7)
                ).count(),
                'top_tags': list(
                    Tag.objects.filter(news__category=category)
                    .annotate(count=Count('news'))
                    .order_by('-count')
                    .values('name', 'count')[:10]
                )
            }
            cache.set(cache_key, stats, 300)  # Cache for 5 minutes
        
        return Response(stats)


@extend_schema_view(
    list=extend_schema(
        summary="List subcategories",
        description="Get a list of subcategories, optionally filtered by category."
    ),
    create=extend_schema(
        summary="Create a new subcategory",
        description="Create a new subcategory within a category."
    ),
)
class SubcategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing news subcategories.
    """
    queryset = Subcategory.objects.filter(is_active=True)
    serializer_class = SubcategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['category', 'is_active']


@extend_schema_view(
    list=extend_schema(
        summary="List tags",
        description="Get a list of tags ordered by usage count."
    ),
    create=extend_schema(
        summary="Create a new tag",
        description="Create a new tag for categorizing news."
    ),
)
class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing news tags.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'description']
    ordering = ['-usage_count', 'name']


@extend_schema_view(
    list=extend_schema(
        summary="List news",
        description="Get a paginated list of news with filtering and search capabilities.",
        parameters=[
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by category ID'
            ),
            OpenApiParameter(
                name='subcategory',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by subcategory ID'
            ),
            OpenApiParameter(
                name='is_urgent',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by urgency'
            ),
            OpenApiParameter(
                name='source',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by source'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in title and content'
            ),
        ]
    ),
    create=extend_schema(
        summary="Create news",
        description="Create a new news article (typically used by webhook receivers)."
    ),
    retrieve=extend_schema(
        summary="Get news details",
        description="Get detailed information about a specific news article."
    ),
    update=extend_schema(
        summary="Update news",
        description="Update an existing news article."
    ),
)
class NewsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing news articles.
    """
    queryset = News.objects.filter(is_published=True)
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = NewsFilter
    search_fields = ['title', 'content', 'summary']
    ordering_fields = ['published_at', 'created_at', 'view_count', 'share_count']
    ordering = ['-published_at']
    pagination_class = NewsPagination
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return NewsListSerializer
        elif self.action == 'create':
            return NewsCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NewsUpdateSerializer
        return NewsDetailSerializer
    
    def get_queryset(self):
        """Get queryset with appropriate filtering."""
        queryset = News.objects.all()
        
        # Filter published news for non-staff users
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_published=True)
        
        return queryset.select_related('category', 'subcategory').prefetch_related('tags')
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve news and increment view count."""
        instance = self.get_object()
        instance.increment_view_count()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Mark news as urgent",
        description="Mark a news article as urgent and trigger notifications."
    )
    @action(detail=True, methods=['post'])
    def mark_urgent(self, request, pk=None):
        """Mark news as urgent."""
        news = self.get_object()
        news.is_urgent = True
        news.save()
        
        # Trigger urgent notification task
        from apps.notifications.tasks import send_urgent_notification
        send_urgent_notification.delay(news.id)
        
        return Response({'status': 'marked as urgent'})
    
    @extend_schema(
        summary="Share news",
        description="Increment share count for a news article."
    )
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Increment share count."""
        news = self.get_object()
        news.increment_share_count()
        return Response({'status': 'shared', 'share_count': news.share_count})
    
    @extend_schema(
        summary="Get related news",
        description="Get news related to this article based on category and tags."
    )
    @action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        """Get related news."""
        news = self.get_object()
        
        # Get related news based on category and tags
        related_news = News.objects.filter(
            Q(category=news.category) | Q(tags__in=news.tags.all())
        ).exclude(id=news.id).filter(is_published=True).distinct()[:5]
        
        serializer = NewsListSerializer(related_news, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Advanced search",
        description="Advanced search with multiple parameters."
    )
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search endpoint."""
        serializer = NewsSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        queryset = self.get_queryset()
        
        # Apply search filters
        if serializer.validated_data.get('q'):
            query = serializer.validated_data['q']
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(content__icontains=query)
            )
        
        if serializer.validated_data.get('category'):
            queryset = queryset.filter(category_id=serializer.validated_data['category'])
        
        if serializer.validated_data.get('subcategory'):
            queryset = queryset.filter(subcategory_id=serializer.validated_data['subcategory'])
        
        if serializer.validated_data.get('tags'):
            queryset = queryset.filter(tags__name__in=serializer.validated_data['tags'])
        
        if serializer.validated_data.get('source'):
            queryset = queryset.filter(source__icontains=serializer.validated_data['source'])
        
        if serializer.validated_data.get('is_urgent') is not None:
            queryset = queryset.filter(is_urgent=serializer.validated_data['is_urgent'])
        
        if serializer.validated_data.get('date_from'):
            queryset = queryset.filter(published_at__gte=serializer.validated_data['date_from'])
        
        if serializer.validated_data.get('date_to'):
            queryset = queryset.filter(published_at__lte=serializer.validated_data['date_to'])
        
        # Apply ordering
        ordering = serializer.validated_data.get('ordering', '-published_at')
        queryset = queryset.order_by(ordering)
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = NewsListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = NewsListSerializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List processing logs",
        description="Get processing logs for news articles."
    ),
)
class NewsProcessingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing news processing logs.
    """
    queryset = NewsProcessingLog.objects.all()
    serializer_class = NewsProcessingLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['news', 'stage', 'status']
    ordering = ['-created_at']


@extend_schema_view(
    list=extend_schema(
        summary="List news statistics",
        description="Get daily news statistics."
    ),
)
class NewsStatisticViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing news statistics.
    """
    queryset = NewsStatistic.objects.all()
    serializer_class = NewsStatisticSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['date']
    ordering = ['-date']