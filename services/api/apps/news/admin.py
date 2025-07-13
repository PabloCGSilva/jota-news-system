"""
Admin configuration for news app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Category, Subcategory, Tag, News, NewsProcessingLog, NewsStatistic


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for Category model."""
    list_display = ['name', 'slug', 'is_active', 'news_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def news_count(self, obj):
        """Get count of news in this category."""
        count = obj.news.count()
        url = reverse('admin:news_news_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    news_count.short_description = 'News Count'


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    """Admin for Subcategory model."""
    list_display = ['name', 'category', 'slug', 'is_active', 'news_count', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def news_count(self, obj):
        """Get count of news in this subcategory."""
        count = obj.news.count()
        url = reverse('admin:news_news_changelist') + f'?subcategory__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    news_count.short_description = 'News Count'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin for Tag model."""
    list_display = ['name', 'slug', 'usage_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    ordering = ['-usage_count', 'name']


class NewsProcessingLogInline(admin.TabularInline):
    """Inline admin for processing logs."""
    model = NewsProcessingLog
    extra = 0
    readonly_fields = ['created_at']
    fields = ['stage', 'status', 'message', 'processing_time', 'created_at']


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    """Admin for News model."""
    list_display = [
        'title', 'category', 'subcategory', 'source', 'author',
        'is_urgent', 'is_published', 'published_at', 'view_count'
    ]
    list_filter = [
        'category', 'subcategory', 'is_urgent', 'is_published',
        'source', 'published_at', 'created_at'
    ]
    search_fields = ['title', 'content', 'source', 'author']
    readonly_fields = [
        'id', 'external_id', 'word_count', 'reading_time',
        'view_count', 'share_count', 'category_confidence',
        'subcategory_confidence', 'urgency_confidence',
        'created_at', 'updated_at'
    ]
    filter_horizontal = ['tags']
    inlines = [NewsProcessingLogInline]
    date_hierarchy = 'published_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'content', 'summary', 'source', 'source_url', 'author')
        }),
        ('Classification', {
            'fields': ('category', 'subcategory', 'tags')
        }),
        ('Status', {
            'fields': ('is_urgent', 'is_published', 'is_processed')
        }),
        ('Metadata', {
            'fields': (
                'external_id', 'published_at', 'word_count', 'reading_time',
                'view_count', 'share_count'
            )
        }),
        ('Confidence Scores', {
            'fields': (
                'category_confidence', 'subcategory_confidence', 'urgency_confidence'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        queryset = super().get_queryset(request)
        return queryset.select_related('category', 'subcategory')
    
    actions = ['mark_urgent', 'mark_not_urgent', 'publish', 'unpublish']
    
    def mark_urgent(self, request, queryset):
        """Mark selected news as urgent."""
        updated = queryset.update(is_urgent=True)
        self.message_user(
            request,
            f'{updated} news articles marked as urgent.'
        )
    mark_urgent.short_description = "Mark selected news as urgent"
    
    def mark_not_urgent(self, request, queryset):
        """Mark selected news as not urgent."""
        updated = queryset.update(is_urgent=False)
        self.message_user(
            request,
            f'{updated} news articles marked as not urgent.'
        )
    mark_not_urgent.short_description = "Mark selected news as not urgent"
    
    def publish(self, request, queryset):
        """Publish selected news."""
        updated = queryset.update(is_published=True)
        self.message_user(
            request,
            f'{updated} news articles published.'
        )
    publish.short_description = "Publish selected news"
    
    def unpublish(self, request, queryset):
        """Unpublish selected news."""
        updated = queryset.update(is_published=False)
        self.message_user(
            request,
            f'{updated} news articles unpublished.'
        )
    unpublish.short_description = "Unpublish selected news"


@admin.register(NewsProcessingLog)
class NewsProcessingLogAdmin(admin.ModelAdmin):
    """Admin for NewsProcessingLog model."""
    list_display = ['news', 'stage', 'status', 'processing_time', 'created_at']
    list_filter = ['stage', 'status', 'created_at']
    search_fields = ['news__title', 'message']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        """Optimize queryset."""
        queryset = super().get_queryset(request)
        return queryset.select_related('news')


@admin.register(NewsStatistic)
class NewsStatisticAdmin(admin.ModelAdmin):
    """Admin for NewsStatistic model."""
    list_display = [
        'date', 'total_news', 'urgent_news', 'avg_processing_time',
        'created_at'
    ]
    list_filter = ['date', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def has_add_permission(self, request):
        """Statistics are generated automatically."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Statistics are read-only."""
        return False