"""
Models for classification app.
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import json


class ClassificationRule(models.Model):
    """
    Rules for automatic news classification.
    """
    RULE_TYPES = [
        ('keyword', 'Keyword Matching'),
        ('pattern', 'Pattern Matching'),
        ('ml', 'Machine Learning'),
        ('hybrid', 'Hybrid'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES, default='keyword')
    
    # Target classification
    target_category = models.ForeignKey(
        'news.Category',
        on_delete=models.CASCADE,
        related_name='classification_rules'
    )
    target_subcategory = models.ForeignKey(
        'news.Subcategory',
        on_delete=models.CASCADE,
        related_name='classification_rules',
        blank=True,
        null=True
    )
    
    # Rule configuration
    keywords = models.JSONField(
        default=list,
        help_text="List of keywords to match"
    )
    patterns = models.JSONField(
        default=list,
        help_text="List of regex patterns to match"
    )
    weight = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text="Weight of this rule in classification"
    )
    confidence_threshold = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Minimum confidence required for this rule to apply"
    )
    
    # Rule conditions
    requires_title_match = models.BooleanField(default=False)
    requires_content_match = models.BooleanField(default=True)
    case_sensitive = models.BooleanField(default=False)
    
    # Status and metrics
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(
        default=100,
        help_text="Priority for rule execution (lower = higher priority)"
    )
    
    # Usage statistics
    total_matches = models.PositiveIntegerField(default=0)
    successful_classifications = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'classification_rule'
        verbose_name = 'Classification Rule'
        verbose_name_plural = 'Classification Rules'
        ordering = ['priority', 'name']
    
    def __str__(self):
        return f"{self.name} → {self.target_category.name}"
    
    def increment_matches(self):
        """Increment total matches counter."""
        self.total_matches += 1
        self.last_used = timezone.now()
        self.save(update_fields=['total_matches', 'last_used'])
    
    def increment_successful_classifications(self):
        """Increment successful classifications counter."""
        self.successful_classifications += 1
        self.save(update_fields=['successful_classifications'])
    
    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        if self.total_matches == 0:
            return 0
        return round((self.successful_classifications / self.total_matches) * 100, 2)


class ClassificationModel(models.Model):
    """
    Machine learning models for news classification.
    """
    MODEL_TYPES = [
        ('tfidf', 'TF-IDF with SVM'),
        ('nb', 'Naive Bayes'),
        ('lr', 'Logistic Regression'),
        ('ensemble', 'Ensemble Model'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    model_type = models.CharField(max_length=20, choices=MODEL_TYPES, default='tfidf')
    
    # Model configuration
    config = models.JSONField(
        default=dict,
        help_text="Model configuration parameters"
    )
    
    # Model files (stored as file paths)
    model_file_path = models.CharField(max_length=255, blank=True)
    vectorizer_file_path = models.CharField(max_length=255, blank=True)
    
    # Training information
    training_data_count = models.PositiveIntegerField(default=0)
    last_trained = models.DateTimeField(null=True, blank=True)
    training_accuracy = models.FloatField(null=True, blank=True)
    validation_accuracy = models.FloatField(null=True, blank=True)
    
    # Model metrics
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=False)
    is_trained = models.BooleanField(default=False)
    
    # Usage statistics
    total_predictions = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'classification_model'
        verbose_name = 'Classification Model'
        verbose_name_plural = 'Classification Models'
        ordering = ['-is_active', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.model_type})"
    
    def increment_predictions(self):
        """Increment predictions counter."""
        self.total_predictions += 1
        self.last_used = timezone.now()
        self.save(update_fields=['total_predictions', 'last_used'])


class ClassificationResult(models.Model):
    """
    Results of news classification attempts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    news = models.ForeignKey(
        'news.News',
        on_delete=models.CASCADE,
        related_name='classification_results'
    )
    
    # Classification method
    method = models.CharField(
        max_length=20,
        choices=[
            ('keyword', 'Keyword Matching'),
            ('ml', 'Machine Learning'),
            ('hybrid', 'Hybrid'),
            ('manual', 'Manual'),
        ],
        default='keyword'
    )
    
    # Applied rule or model
    applied_rule = models.ForeignKey(
        ClassificationRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='results'
    )
    applied_model = models.ForeignKey(
        ClassificationModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='results'
    )
    
    # Classification results
    predicted_category = models.ForeignKey(
        'news.Category',
        on_delete=models.CASCADE,
        related_name='predicted_results'
    )
    predicted_subcategory = models.ForeignKey(
        'news.Subcategory',
        on_delete=models.CASCADE,
        related_name='predicted_results',
        blank=True,
        null=True
    )
    
    # Confidence scores
    category_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    subcategory_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0
    )
    urgency_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0
    )
    
    # Prediction details
    prediction_details = models.JSONField(
        default=dict,
        help_text="Detailed prediction information"
    )
    
    # Status
    is_accepted = models.BooleanField(default=False)
    is_manual_override = models.BooleanField(default=False)
    
    # Processing metrics
    processing_time = models.FloatField(
        help_text="Time taken for classification in seconds"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'classification_result'
        verbose_name = 'Classification Result'
        verbose_name_plural = 'Classification Results'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.news.title} → {self.predicted_category.name}"
    
    def accept_classification(self):
        """Accept this classification and apply it to the news."""
        self.is_accepted = True
        self.save()
        
        # Update news with classification
        self.news.category = self.predicted_category
        self.news.subcategory = self.predicted_subcategory
        self.news.category_confidence = self.category_confidence
        self.news.subcategory_confidence = self.subcategory_confidence
        self.news.urgency_confidence = self.urgency_confidence
        self.news.is_processed = True
        self.news.save()
        
        # Update rule/model statistics
        if self.applied_rule:
            self.applied_rule.increment_successful_classifications()
        if self.applied_model:
            # Update model statistics if needed
            pass


class ClassificationTrainingData(models.Model):
    """
    Training data for machine learning models.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    news = models.ForeignKey(
        'news.News',
        on_delete=models.CASCADE,
        related_name='training_data'
    )
    
    # Labels
    category = models.ForeignKey(
        'news.Category',
        on_delete=models.CASCADE,
        related_name='training_data'
    )
    subcategory = models.ForeignKey(
        'news.Subcategory',
        on_delete=models.CASCADE,
        related_name='training_data',
        blank=True,
        null=True
    )
    is_urgent = models.BooleanField(default=False)
    
    # Data source
    source = models.CharField(
        max_length=20,
        choices=[
            ('manual', 'Manual Labeling'),
            ('verified', 'Verified Classification'),
            ('automatic', 'Automatic Classification'),
        ],
        default='manual'
    )
    
    # Quality indicators
    confidence_score = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    is_validated = models.BooleanField(default=False)
    
    # Usage tracking
    used_in_training = models.BooleanField(default=False)
    last_used = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'classification_training_data'
        verbose_name = 'Classification Training Data'
        verbose_name_plural = 'Classification Training Data'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.news.title} → {self.category.name}"


class ClassificationStatistic(models.Model):
    """
    Daily classification statistics.
    """
    date = models.DateField(unique=True)
    
    # Overall statistics
    total_classifications = models.PositiveIntegerField(default=0)
    successful_classifications = models.PositiveIntegerField(default=0)
    failed_classifications = models.PositiveIntegerField(default=0)
    
    # Method breakdown
    keyword_classifications = models.PositiveIntegerField(default=0)
    ml_classifications = models.PositiveIntegerField(default=0)
    hybrid_classifications = models.PositiveIntegerField(default=0)
    manual_classifications = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    avg_processing_time = models.FloatField(default=0.0)
    avg_confidence_score = models.FloatField(default=0.0)
    
    # Category breakdown
    category_breakdown = models.JSONField(
        default=dict,
        help_text="Number of classifications per category"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'classification_statistic'
        verbose_name = 'Classification Statistic'
        verbose_name_plural = 'Classification Statistics'
        ordering = ['-date']
    
    def __str__(self):
        return f"Classification Statistics for {self.date}"
    
    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        if self.total_classifications == 0:
            return 0
        return round((self.successful_classifications / self.total_classifications) * 100, 2)