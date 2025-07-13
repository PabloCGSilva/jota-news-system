"""
Serializers for news app.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import Category, Subcategory, Tag, News, NewsProcessingLog, NewsStatistic


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer."""
    news_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'keywords',
            'is_active', 'news_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_news_count(self, obj):
        """Get count of news in this category."""
        return obj.news.filter(is_published=True).count()


class SubcategorySerializer(serializers.ModelSerializer):
    """Subcategory serializer."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    news_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Subcategory
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'category_name', 'keywords', 'is_active', 'news_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_news_count(self, obj):
        """Get count of news in this subcategory."""
        return obj.news.filter(is_published=True).count()


class TagSerializer(serializers.ModelSerializer):
    """Tag serializer."""
    
    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'slug', 'description', 'usage_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']


class NewsListSerializer(serializers.ModelSerializer):
    """News list serializer (for list views)."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = News
        fields = [
            'id', 'title', 'summary', 'source', 'author',
            'published_at', 'category', 'category_name',
            'subcategory', 'subcategory_name', 'tags',
            'is_urgent', 'is_published', 'word_count',
            'reading_time', 'view_count', 'share_count'
        ]


class NewsDetailSerializer(serializers.ModelSerializer):
    """News detail serializer (for detail views)."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = News
        fields = [
            'id', 'title', 'content', 'summary', 'source',
            'source_url', 'author', 'published_at', 'external_id',
            'category', 'category_name', 'subcategory', 'subcategory_name',
            'tags', 'is_urgent', 'is_published', 'is_processed',
            'category_confidence', 'subcategory_confidence', 'urgency_confidence',
            'word_count', 'reading_time', 'view_count', 'share_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'external_id', 'is_processed', 'category_confidence',
            'subcategory_confidence', 'urgency_confidence', 'word_count',
            'reading_time', 'view_count', 'share_count', 'created_at', 'updated_at'
        ]


class NewsCreateSerializer(serializers.ModelSerializer):
    """News create serializer (for creating news via API)."""
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = News
        fields = [
            'title', 'content', 'summary', 'source', 'source_url',
            'author', 'published_at', 'external_id', 'category',
            'subcategory', 'tag_names', 'is_urgent', 'is_published'
        ]
    
    def create(self, validated_data):
        """Create news with tags."""
        tag_names = validated_data.pop('tag_names', [])
        news = News.objects.create(**validated_data)
        
        # Create or get tags
        if tag_names:
            tags = []
            for tag_name in tag_names:
                tag, created = Tag.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': tag_name.lower().replace(' ', '-')}
                )
                tags.append(tag)
            news.tags.set(tags)
        
        return news


class NewsUpdateSerializer(serializers.ModelSerializer):
    """News update serializer (for editorial team)."""
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = News
        fields = [
            'title', 'content', 'summary', 'category', 'subcategory',
            'tag_names', 'is_urgent', 'is_published'
        ]
    
    def update(self, instance, validated_data):
        """Update news with tags."""
        tag_names = validated_data.pop('tag_names', None)
        
        # Update news fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update tags if provided
        if tag_names is not None:
            tags = []
            for tag_name in tag_names:
                tag, created = Tag.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': tag_name.lower().replace(' ', '-')}
                )
                tags.append(tag)
            instance.tags.set(tags)
        
        return instance


class NewsProcessingLogSerializer(serializers.ModelSerializer):
    """News processing log serializer."""
    
    class Meta:
        model = NewsProcessingLog
        fields = [
            'id', 'news', 'stage', 'status', 'message',
            'processing_time', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NewsStatisticSerializer(serializers.ModelSerializer):
    """News statistic serializer."""
    
    class Meta:
        model = NewsStatistic
        fields = [
            'id', 'date', 'total_news', 'urgent_news',
            'categories_count', 'sources_count', 'avg_processing_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NewsSearchSerializer(serializers.Serializer):
    """News search parameters serializer."""
    q = serializers.CharField(required=False, help_text="Search query")
    category = serializers.UUIDField(required=False, help_text="Filter by category ID")
    subcategory = serializers.UUIDField(required=False, help_text="Filter by subcategory ID")
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Filter by tag names"
    )
    source = serializers.CharField(required=False, help_text="Filter by source")
    is_urgent = serializers.BooleanField(required=False, help_text="Filter by urgency")
    date_from = serializers.DateTimeField(required=False, help_text="Published after this date")
    date_to = serializers.DateTimeField(required=False, help_text="Published before this date")
    ordering = serializers.ChoiceField(
        choices=[
            '-published_at', 'published_at',
            '-created_at', 'created_at',
            '-view_count', 'view_count',
            '-share_count', 'share_count'
        ],
        default='-published_at',
        help_text="Order results by field"
    )