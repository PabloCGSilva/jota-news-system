"""
Serializers for classification app.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import (
    ClassificationRule, ClassificationModel, ClassificationResult,
    ClassificationTrainingData, ClassificationStatistic
)


class ClassificationRuleSerializer(serializers.ModelSerializer):
    """Classification rule serializer."""
    target_category_name = serializers.CharField(source='target_category.name', read_only=True)
    target_subcategory_name = serializers.CharField(source='target_subcategory.name', read_only=True)
    
    class Meta:
        model = ClassificationRule
        fields = [
            'id', 'name', 'description', 'rule_type', 'target_category',
            'target_category_name', 'target_subcategory', 'target_subcategory_name',
            'keywords', 'patterns', 'weight', 'confidence_threshold',
            'requires_title_match', 'requires_content_match', 'case_sensitive',
            'is_active', 'priority', 'total_matches', 'successful_classifications',
            'success_rate', 'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_matches', 'successful_classifications', 'success_rate',
            'last_used', 'created_at', 'updated_at'
        ]


class ClassificationModelSerializer(serializers.ModelSerializer):
    """Classification model serializer."""
    
    class Meta:
        model = ClassificationModel
        fields = [
            'id', 'name', 'description', 'model_type', 'config',
            'model_file_path', 'vectorizer_file_path', 'training_data_count',
            'last_trained', 'training_accuracy', 'validation_accuracy',
            'precision', 'recall', 'f1_score', 'is_active', 'is_trained',
            'total_predictions', 'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'model_file_path', 'vectorizer_file_path', 'training_data_count',
            'last_trained', 'training_accuracy', 'validation_accuracy',
            'precision', 'recall', 'f1_score', 'is_trained',
            'total_predictions', 'last_used', 'created_at', 'updated_at'
        ]


class ClassificationResultSerializer(serializers.ModelSerializer):
    """Classification result serializer."""
    news_title = serializers.CharField(source='news.title', read_only=True)
    predicted_category_name = serializers.CharField(source='predicted_category.name', read_only=True)
    predicted_subcategory_name = serializers.CharField(source='predicted_subcategory.name', read_only=True)
    applied_rule_name = serializers.CharField(source='applied_rule.name', read_only=True)
    applied_model_name = serializers.CharField(source='applied_model.name', read_only=True)
    
    class Meta:
        model = ClassificationResult
        fields = [
            'id', 'news', 'news_title', 'method', 'applied_rule', 'applied_rule_name',
            'applied_model', 'applied_model_name', 'predicted_category',
            'predicted_category_name', 'predicted_subcategory', 'predicted_subcategory_name',
            'category_confidence', 'subcategory_confidence', 'urgency_confidence',
            'prediction_details', 'is_accepted', 'is_manual_override',
            'processing_time', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ClassificationTrainingDataSerializer(serializers.ModelSerializer):
    """Classification training data serializer."""
    news_title = serializers.CharField(source='news.title', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    
    class Meta:
        model = ClassificationTrainingData
        fields = [
            'id', 'news', 'news_title', 'category', 'category_name',
            'subcategory', 'subcategory_name', 'is_urgent', 'source',
            'confidence_score', 'is_validated', 'used_in_training',
            'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_used', 'created_at', 'updated_at']


class ClassificationStatisticSerializer(serializers.ModelSerializer):
    """Classification statistic serializer."""
    
    class Meta:
        model = ClassificationStatistic
        fields = [
            'id', 'date', 'total_classifications', 'successful_classifications',
            'failed_classifications', 'success_rate', 'keyword_classifications',
            'ml_classifications', 'hybrid_classifications', 'manual_classifications',
            'avg_processing_time', 'avg_confidence_score', 'category_breakdown',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NewsClassificationSerializer(serializers.Serializer):
    """Serializer for manual news classification."""
    news_id = serializers.UUIDField()
    method = serializers.ChoiceField(
        choices=['keyword', 'ml', 'hybrid'],
        default='hybrid'
    )
    force_reclassify = serializers.BooleanField(default=False)
    
    def validate_news_id(self, value):
        """Validate news exists."""
        from apps.news.models import News
        try:
            News.objects.get(id=value)
        except News.DoesNotExist:
            raise serializers.ValidationError("News not found")
        return value


class BulkClassificationSerializer(serializers.Serializer):
    """Serializer for bulk classification."""
    news_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    method = serializers.ChoiceField(
        choices=['keyword', 'ml', 'hybrid'],
        default='hybrid'
    )
    force_reclassify = serializers.BooleanField(default=False)
    
    def validate_news_ids(self, value):
        """Validate all news exist."""
        from apps.news.models import News
        existing_ids = News.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)
        
        if missing_ids:
            raise serializers.ValidationError(
                f"News not found: {', '.join(str(id) for id in missing_ids)}"
            )
        return value


class ModelTrainingSerializer(serializers.Serializer):
    """Serializer for model training."""
    model_id = serializers.UUIDField()
    use_all_validated_data = serializers.BooleanField(default=True)
    min_samples_per_category = serializers.IntegerField(default=10)
    
    def validate_model_id(self, value):
        """Validate model exists."""
        try:
            ClassificationModel.objects.get(id=value)
        except ClassificationModel.DoesNotExist:
            raise serializers.ValidationError("Model not found")
        return value


class ClassificationStatsSerializer(serializers.Serializer):
    """Serializer for classification statistics."""
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    
    def validate(self, data):
        """Validate date range."""
        if data.get('date_from') and data.get('date_to'):
            if data['date_from'] > data['date_to']:
                raise serializers.ValidationError("date_from must be before date_to")
        return data


class ClassificationRuleTestSerializer(serializers.Serializer):
    """Serializer for testing classification rules."""
    rule_id = serializers.UUIDField()
    text = serializers.CharField(max_length=1000)
    
    def validate_rule_id(self, value):
        """Validate rule exists."""
        try:
            ClassificationRule.objects.get(id=value)
        except ClassificationRule.DoesNotExist:
            raise serializers.ValidationError("Rule not found")
        return value