"""
News models for JOTA News System.
"""
from django.db import models
from django.core.validators import MaxLengthValidator
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
import uuid


class BaseModel(models.Model):
    """Base model with common fields."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Category(BaseModel):
    """News category model."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    keywords = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="Keywords for automatic classification"
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'news_category'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Subcategory(BaseModel):
    """News subcategory model."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories'
    )
    keywords = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="Keywords for automatic classification"
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'news_subcategory'
        verbose_name = 'Subcategory'
        verbose_name_plural = 'Subcategories'
        unique_together = ['category', 'slug']
        ordering = ['category__name', 'name']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Tag(BaseModel):
    """News tag model."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'news_tag'
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ['-usage_count', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class News(BaseModel):
    """Main news model."""
    title = models.CharField(
        max_length=200,
        validators=[MaxLengthValidator(200)]
    )
    content = models.TextField(
        validators=[MaxLengthValidator(10000)]
    )
    summary = models.TextField(blank=True, max_length=500)
    
    # Source information
    source = models.CharField(max_length=200)
    source_url = models.URLField(blank=True)
    author = models.CharField(max_length=200, blank=True)
    
    # Publication information
    published_at = models.DateTimeField(default=timezone.now)
    external_id = models.CharField(max_length=200, blank=True, null=True, unique=True)
    
    # Classification
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='news'
    )
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.PROTECT,
        related_name='news',
        blank=True,
        null=True
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='news')
    
    # Status and priority
    is_urgent = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    is_processed = models.BooleanField(default=False)
    
    # Classification confidence scores
    category_confidence = models.FloatField(default=0.0)
    subcategory_confidence = models.FloatField(default=0.0)
    urgency_confidence = models.FloatField(default=0.0)
    
    # Metadata
    word_count = models.PositiveIntegerField(default=0)
    reading_time = models.PositiveIntegerField(default=0)  # in minutes
    
    # Engagement metrics
    view_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'news_news'
        verbose_name = 'News'
        verbose_name_plural = 'News'
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['category', '-published_at']),
            models.Index(fields=['subcategory', '-published_at']),
            models.Index(fields=['is_urgent', '-published_at']),
            models.Index(fields=['is_published', '-published_at']),
            models.Index(fields=['source', '-published_at']),
            GinIndex(fields=['title', 'content']),  # Full-text search
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        """Override save to calculate derived fields."""
        # Calculate word count
        self.word_count = len(self.content.split())
        
        # Calculate reading time (assuming 200 words per minute)
        self.reading_time = max(1, self.word_count // 200)
        
        # Generate summary if not provided
        if not self.summary and self.content:
            self.summary = self.content[:497] + '...' if len(self.content) > 500 else self.content
        
        super().save(*args, **kwargs)
    
    def increment_view_count(self):
        """Increment view count."""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_share_count(self):
        """Increment share count."""
        self.share_count += 1
        self.save(update_fields=['share_count'])


class NewsProcessingLog(BaseModel):
    """Log of news processing activities."""
    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name='processing_logs'
    )
    stage = models.CharField(max_length=50)  # e.g., 'received', 'classified', 'published'
    status = models.CharField(max_length=20)  # e.g., 'success', 'error', 'pending'
    message = models.TextField(blank=True)
    processing_time = models.FloatField(default=0.0)  # in seconds
    
    class Meta:
        db_table = 'news_processing_log'
        verbose_name = 'Processing Log'
        verbose_name_plural = 'Processing Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.news.title} - {self.stage} - {self.status}"


class NewsStatistic(BaseModel):
    """Daily news statistics."""
    date = models.DateField(unique=True)
    total_news = models.PositiveIntegerField(default=0)
    urgent_news = models.PositiveIntegerField(default=0)
    categories_count = models.JSONField(default=dict)  # {"category_name": count}
    sources_count = models.JSONField(default=dict)  # {"source_name": count}
    avg_processing_time = models.FloatField(default=0.0)
    
    class Meta:
        db_table = 'news_statistic'
        verbose_name = 'News Statistic'
        verbose_name_plural = 'News Statistics'
        ordering = ['-date']
    
    def __str__(self):
        return f"Statistics for {self.date}"