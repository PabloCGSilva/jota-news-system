"""
Admin configuration for classification app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    ClassificationRule, ClassificationModel, ClassificationResult,
    ClassificationTrainingData, ClassificationStatistic
)


@admin.register(ClassificationRule)
class ClassificationRuleAdmin(admin.ModelAdmin):
    """Admin for ClassificationRule model."""
    list_display = [
        'name', 'rule_type', 'target_category', 'target_subcategory',
        'weight', 'is_active', 'success_rate_display', 'total_matches',
        'priority'
    ]
    list_filter = ['rule_type', 'is_active', 'target_category', 'requires_title_match']
    search_fields = ['name', 'description', 'keywords', 'target_category__name']
    readonly_fields = [
        'total_matches', 'successful_classifications', 'success_rate',
        'last_used', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'rule_type', 'is_active', 'priority')
        }),
        ('Target Classification', {
            'fields': ('target_category', 'target_subcategory')
        }),
        ('Rule Configuration', {
            'fields': ('keywords', 'patterns', 'weight', 'confidence_threshold')
        }),
        ('Matching Options', {
            'fields': ('requires_title_match', 'requires_content_match', 'case_sensitive')
        }),
        ('Statistics', {
            'fields': ('total_matches', 'successful_classifications', 'success_rate', 'last_used'),
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
        if rate >= 80:
            color = 'green'
        elif rate >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'
    
    actions = ['activate_rules', 'deactivate_rules', 'reset_statistics']
    
    def activate_rules(self, request, queryset):
        """Activate selected rules."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} rules activated.')
    activate_rules.short_description = "Activate selected rules"
    
    def deactivate_rules(self, request, queryset):
        """Deactivate selected rules."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} rules deactivated.')
    deactivate_rules.short_description = "Deactivate selected rules"
    
    def reset_statistics(self, request, queryset):
        """Reset statistics for selected rules."""
        updated = queryset.update(
            total_matches=0,
            successful_classifications=0,
            last_used=None
        )
        self.message_user(request, f'Statistics reset for {updated} rules.')
    reset_statistics.short_description = "Reset statistics"


@admin.register(ClassificationModel)
class ClassificationModelAdmin(admin.ModelAdmin):
    """Admin for ClassificationModel model."""
    list_display = [
        'name', 'model_type', 'is_active', 'is_trained',
        'training_accuracy_display', 'total_predictions', 'last_trained'
    ]
    list_filter = ['model_type', 'is_active', 'is_trained', 'last_trained']
    search_fields = ['name', 'description']
    readonly_fields = [
        'model_file_path', 'vectorizer_file_path', 'training_data_count',
        'last_trained', 'training_accuracy', 'validation_accuracy',
        'precision', 'recall', 'f1_score', 'is_trained',
        'total_predictions', 'last_used', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'model_type', 'is_active')
        }),
        ('Configuration', {
            'fields': ('config',)
        }),
        ('Model Files', {
            'fields': ('model_file_path', 'vectorizer_file_path'),
            'classes': ('collapse',)
        }),
        ('Training Information', {
            'fields': (
                'training_data_count', 'last_trained', 'training_accuracy',
                'validation_accuracy', 'is_trained'
            ),
            'classes': ('collapse',)
        }),
        ('Performance Metrics', {
            'fields': ('precision', 'recall', 'f1_score'),
            'classes': ('collapse',)
        }),
        ('Usage Statistics', {
            'fields': ('total_predictions', 'last_used'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def training_accuracy_display(self, obj):
        """Display training accuracy with color coding."""
        if obj.training_accuracy is None:
            return 'Not trained'
        
        accuracy = obj.training_accuracy * 100
        if accuracy >= 90:
            color = 'green'
        elif accuracy >= 80:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, accuracy
        )
    training_accuracy_display.short_description = 'Training Accuracy'
    
    actions = ['activate_models', 'deactivate_models']
    
    def activate_models(self, request, queryset):
        """Activate selected models."""
        updated = queryset.filter(is_trained=True).update(is_active=True)
        self.message_user(request, f'{updated} trained models activated.')
    activate_models.short_description = "Activate selected models"
    
    def deactivate_models(self, request, queryset):
        """Deactivate selected models."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} models deactivated.')
    deactivate_models.short_description = "Deactivate selected models"


@admin.register(ClassificationResult)
class ClassificationResultAdmin(admin.ModelAdmin):
    """Admin for ClassificationResult model."""
    list_display = [
        'news_title_short', 'method', 'predicted_category',
        'category_confidence_display', 'is_accepted', 'processing_time',
        'created_at'
    ]
    list_filter = ['method', 'is_accepted', 'predicted_category', 'created_at']
    search_fields = ['news__title', 'predicted_category__name']
    readonly_fields = [
        'news', 'method', 'applied_rule', 'applied_model',
        'predicted_category', 'predicted_subcategory',
        'category_confidence', 'subcategory_confidence', 'urgency_confidence',
        'prediction_details', 'processing_time', 'created_at'
    ]
    
    fieldsets = (
        ('News Information', {
            'fields': ('news',)
        }),
        ('Classification Method', {
            'fields': ('method', 'applied_rule', 'applied_model')
        }),
        ('Prediction Results', {
            'fields': (
                'predicted_category', 'predicted_subcategory',
                'category_confidence', 'subcategory_confidence', 'urgency_confidence'
            )
        }),
        ('Status', {
            'fields': ('is_accepted', 'is_manual_override')
        }),
        ('Details', {
            'fields': ('prediction_details', 'processing_time'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def news_title_short(self, obj):
        """Show truncated news title."""
        title = obj.news.title
        return title[:50] + '...' if len(title) > 50 else title
    news_title_short.short_description = 'News Title'
    
    def category_confidence_display(self, obj):
        """Display confidence with color coding."""
        confidence = obj.category_confidence * 100
        if confidence >= 80:
            color = 'green'
        elif confidence >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, confidence
        )
    category_confidence_display.short_description = 'Confidence'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'news', 'predicted_category', 'predicted_subcategory',
            'applied_rule', 'applied_model'
        )
    
    def has_add_permission(self, request):
        """Results are created automatically."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Limited editing allowed."""
        return request.user.is_superuser
    
    actions = ['accept_classifications', 'reject_classifications']
    
    def accept_classifications(self, request, queryset):
        """Accept selected classifications."""
        count = 0
        for result in queryset.filter(is_accepted=False):
            result.accept_classification()
            count += 1
        self.message_user(request, f'{count} classifications accepted.')
    accept_classifications.short_description = "Accept selected classifications"
    
    def reject_classifications(self, request, queryset):
        """Reject selected classifications."""
        updated = queryset.update(is_manual_override=True)
        self.message_user(request, f'{updated} classifications rejected.')
    reject_classifications.short_description = "Reject selected classifications"


@admin.register(ClassificationTrainingData)
class ClassificationTrainingDataAdmin(admin.ModelAdmin):
    """Admin for ClassificationTrainingData model."""
    list_display = [
        'news_title_short', 'category', 'subcategory', 'source',
        'is_validated', 'used_in_training', 'confidence_score',
        'created_at'
    ]
    list_filter = ['category', 'source', 'is_validated', 'used_in_training', 'created_at']
    search_fields = ['news__title', 'category__name']
    readonly_fields = ['last_used', 'created_at', 'updated_at']
    
    fieldsets = (
        ('News Information', {
            'fields': ('news',)
        }),
        ('Labels', {
            'fields': ('category', 'subcategory', 'is_urgent')
        }),
        ('Data Source', {
            'fields': ('source', 'confidence_score')
        }),
        ('Usage', {
            'fields': ('is_validated', 'used_in_training', 'last_used')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def news_title_short(self, obj):
        """Show truncated news title."""
        title = obj.news.title
        return title[:50] + '...' if len(title) > 50 else title
    news_title_short.short_description = 'News Title'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'news', 'category', 'subcategory'
        )
    
    actions = ['validate_data', 'mark_for_training', 'remove_from_training']
    
    def validate_data(self, request, queryset):
        """Validate selected training data."""
        updated = queryset.update(is_validated=True)
        self.message_user(request, f'{updated} training data entries validated.')
    validate_data.short_description = "Validate selected data"
    
    def mark_for_training(self, request, queryset):
        """Mark for training."""
        updated = queryset.update(used_in_training=True, is_validated=True)
        self.message_user(request, f'{updated} entries marked for training.')
    mark_for_training.short_description = "Mark for training"
    
    def remove_from_training(self, request, queryset):
        """Remove from training."""
        updated = queryset.update(used_in_training=False)
        self.message_user(request, f'{updated} entries removed from training.')
    remove_from_training.short_description = "Remove from training"


@admin.register(ClassificationStatistic)
class ClassificationStatisticAdmin(admin.ModelAdmin):
    """Admin for ClassificationStatistic model."""
    list_display = [
        'date', 'total_classifications', 'successful_classifications',
        'success_rate_display', 'avg_processing_time', 'avg_confidence_score'
    ]
    list_filter = ['date', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def success_rate_display(self, obj):
        """Display success rate with color coding."""
        rate = obj.success_rate
        if rate >= 80:
            color = 'green'
        elif rate >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'
    
    def has_add_permission(self, request):
        """Statistics are generated automatically."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Statistics are read-only."""
        return False