"""
Filters for news app.
"""
import django_filters
from django.db.models import Q
from .models import News, Category, Subcategory, Tag


class NewsFilter(django_filters.FilterSet):
    """
    Filter set for news articles.
    """
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.filter(is_active=True),
        help_text="Filter by category"
    )
    
    subcategory = django_filters.ModelChoiceFilter(
        queryset=Subcategory.objects.filter(is_active=True),
        help_text="Filter by subcategory"
    )
    
    tags = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        help_text="Filter by tags"
    )
    
    source = django_filters.CharFilter(
        lookup_expr='icontains',
        help_text="Filter by source name"
    )
    
    author = django_filters.CharFilter(
        lookup_expr='icontains',
        help_text="Filter by author name"
    )
    
    is_urgent = django_filters.BooleanFilter(
        help_text="Filter by urgency status"
    )
    
    is_published = django_filters.BooleanFilter(
        help_text="Filter by publication status"
    )
    
    published_date = django_filters.DateFromToRangeFilter(
        field_name='published_at',
        help_text="Filter by publication date range"
    )
    
    created_date = django_filters.DateFromToRangeFilter(
        field_name='created_at',
        help_text="Filter by creation date range"
    )
    
    word_count = django_filters.RangeFilter(
        help_text="Filter by word count range"
    )
    
    reading_time = django_filters.RangeFilter(
        help_text="Filter by reading time range (minutes)"
    )
    
    title_search = django_filters.CharFilter(
        field_name='title',
        lookup_expr='icontains',
        help_text="Search in title"
    )
    
    content_search = django_filters.CharFilter(
        field_name='content',
        lookup_expr='icontains',
        help_text="Search in content"
    )
    
    full_text_search = django_filters.CharFilter(
        method='filter_full_text',
        help_text="Full text search in title and content"
    )
    
    has_external_id = django_filters.BooleanFilter(
        method='filter_has_external_id',
        help_text="Filter by presence of external ID"
    )
    
    confidence_threshold = django_filters.NumberFilter(
        method='filter_confidence_threshold',
        help_text="Filter by minimum classification confidence"
    )
    
    class Meta:
        model = News
        fields = [
            'category', 'subcategory', 'tags', 'source', 'author',
            'is_urgent', 'is_published', 'published_date', 'created_date',
            'word_count', 'reading_time'
        ]
    
    def filter_full_text(self, queryset, name, value):
        """
        Full text search in title and content.
        """
        if value:
            return queryset.filter(
                Q(title__icontains=value) | Q(content__icontains=value)
            )
        return queryset
    
    def filter_has_external_id(self, queryset, name, value):
        """
        Filter by presence of external ID.
        """
        if value:
            return queryset.exclude(external_id__isnull=True).exclude(external_id='')
        else:
            return queryset.filter(Q(external_id__isnull=True) | Q(external_id=''))
    
    def filter_confidence_threshold(self, queryset, name, value):
        """
        Filter by minimum classification confidence.
        """
        if value is not None:
            return queryset.filter(
                Q(category_confidence__gte=value) |
                Q(subcategory_confidence__gte=value) |
                Q(urgency_confidence__gte=value)
            )
        return queryset


class CategoryFilter(django_filters.FilterSet):
    """
    Filter set for categories.
    """
    name = django_filters.CharFilter(
        lookup_expr='icontains',
        help_text="Filter by category name"
    )
    
    has_news = django_filters.BooleanFilter(
        method='filter_has_news',
        help_text="Filter categories that have news"
    )
    
    keyword_search = django_filters.CharFilter(
        method='filter_keyword_search',
        help_text="Search in category keywords"
    )
    
    class Meta:
        model = Category
        fields = ['name', 'is_active']
    
    def filter_has_news(self, queryset, name, value):
        """
        Filter categories that have news.
        """
        if value:
            return queryset.filter(news__isnull=False).distinct()
        else:
            return queryset.filter(news__isnull=True).distinct()
    
    def filter_keyword_search(self, queryset, name, value):
        """
        Search in category keywords.
        """
        if value:
            return queryset.filter(keywords__icontains=value)
        return queryset


class TagFilter(django_filters.FilterSet):
    """
    Filter set for tags.
    """
    name = django_filters.CharFilter(
        lookup_expr='icontains',
        help_text="Filter by tag name"
    )
    
    usage_count = django_filters.RangeFilter(
        help_text="Filter by usage count range"
    )
    
    min_usage = django_filters.NumberFilter(
        field_name='usage_count',
        lookup_expr='gte',
        help_text="Minimum usage count"
    )
    
    has_news = django_filters.BooleanFilter(
        method='filter_has_news',
        help_text="Filter tags that have news"
    )
    
    class Meta:
        model = Tag
        fields = ['name', 'usage_count']
    
    def filter_has_news(self, queryset, name, value):
        """
        Filter tags that have news.
        """
        if value:
            return queryset.filter(news__isnull=False).distinct()
        else:
            return queryset.filter(news__isnull=True).distinct()