"""
Views for classification app.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Avg
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import (
    ClassificationRule, ClassificationModel, ClassificationResult,
    ClassificationTrainingData, ClassificationStatistic
)
from .serializers import (
    ClassificationRuleSerializer, ClassificationModelSerializer,
    ClassificationResultSerializer, ClassificationTrainingDataSerializer,
    ClassificationStatisticSerializer, NewsClassificationSerializer,
    BulkClassificationSerializer, ModelTrainingSerializer,
    ClassificationStatsSerializer, ClassificationRuleTestSerializer
)
from .tasks import (
    classify_news, train_classification_model, bulk_classify_news,
    retrain_models, generate_training_data
)
from .classifier import classifier

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="List classification rules",
        description="Get a list of all classification rules with their performance metrics."
    ),
    create=extend_schema(
        summary="Create classification rule",
        description="Create a new classification rule for automatic news categorization."
    ),
    retrieve=extend_schema(
        summary="Get classification rule details",
        description="Get detailed information about a specific classification rule."
    ),
    update=extend_schema(
        summary="Update classification rule",
        description="Update an existing classification rule."
    ),
)
class ClassificationRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing classification rules.
    """
    queryset = ClassificationRule.objects.all()
    serializer_class = ClassificationRuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['rule_type', 'is_active', 'target_category']
    ordering = ['priority', 'name']
    
    @extend_schema(
        summary="Test classification rule",
        description="Test a classification rule against sample text."
    )
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test classification rule against sample text."""
        rule = self.get_object()
        serializer = ClassificationRuleTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        text = serializer.validated_data['text']
        
        # Simple keyword matching test
        matches = []
        text_lower = text.lower()
        
        for keyword in rule.keywords:
            if keyword.lower() in text_lower:
                matches.append(keyword)
        
        confidence = len(matches) / max(len(rule.keywords), 1)
        would_match = confidence >= rule.confidence_threshold
        
        return Response({
            'rule': rule.name,
            'text': text,
            'matches': matches,
            'confidence': confidence,
            'threshold': rule.confidence_threshold,
            'would_match': would_match
        })
    
    @extend_schema(
        summary="Get rule performance",
        description="Get performance statistics for a classification rule."
    )
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get rule performance statistics."""
        rule = self.get_object()
        
        # Get recent results
        recent_results = ClassificationResult.objects.filter(
            applied_rule=rule,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        )
        
        stats = {
            'total_uses': rule.total_matches,
            'successful_classifications': rule.successful_classifications,
            'success_rate': rule.success_rate,
            'recent_uses': recent_results.count(),
            'recent_accuracy': recent_results.filter(is_accepted=True).count() / max(recent_results.count(), 1) * 100,
            'last_used': rule.last_used,
            'categories_predicted': list(
                recent_results.values('predicted_category__name')
                .annotate(count=Count('id'))
                .order_by('-count')
            )
        }
        
        return Response(stats)


@extend_schema_view(
    list=extend_schema(
        summary="List classification models",
        description="Get a list of all machine learning models for classification."
    ),
    create=extend_schema(
        summary="Create classification model",
        description="Create a new machine learning model configuration."
    ),
)
class ClassificationModelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing classification models.
    """
    queryset = ClassificationModel.objects.all()
    serializer_class = ClassificationModelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['model_type', 'is_active', 'is_trained']
    ordering = ['-is_active', 'name']
    
    @extend_schema(
        summary="Train classification model",
        description="Train a machine learning model with available training data."
    )
    @action(detail=True, methods=['post'])
    def train(self, request, pk=None):
        """Train the classification model."""
        model = self.get_object()
        
        # Check if training data is available
        training_data_count = ClassificationTrainingData.objects.filter(
            is_validated=True,
            used_in_training=True
        ).count()
        
        if training_data_count < 50:
            return Response(
                {'error': f'Insufficient training data. Found {training_data_count}, need at least 50 samples.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start training task
        task = train_classification_model.delay(model.id)
        
        return Response({
            'message': 'Model training started',
            'task_id': task.id,
            'training_data_count': training_data_count
        })
    
    @extend_schema(
        summary="Get model performance",
        description="Get performance metrics for a classification model."
    )
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get model performance metrics."""
        model = self.get_object()
        
        # Get recent predictions
        recent_results = ClassificationResult.objects.filter(
            applied_model=model,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        )
        
        stats = {
            'training_accuracy': model.training_accuracy,
            'validation_accuracy': model.validation_accuracy,
            'precision': model.precision,
            'recall': model.recall,
            'f1_score': model.f1_score,
            'total_predictions': model.total_predictions,
            'recent_predictions': recent_results.count(),
            'recent_accuracy': recent_results.filter(is_accepted=True).count() / max(recent_results.count(), 1) * 100,
            'last_trained': model.last_trained,
            'last_used': model.last_used,
            'training_data_count': model.training_data_count
        }
        
        return Response(stats)


@extend_schema_view(
    list=extend_schema(
        summary="List classification results",
        description="Get a list of classification results with filtering options."
    ),
    retrieve=extend_schema(
        summary="Get classification result details",
        description="Get detailed information about a specific classification result."
    ),
)
class ClassificationResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing classification results.
    """
    queryset = ClassificationResult.objects.all()
    serializer_class = ClassificationResultSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['method', 'is_accepted', 'predicted_category']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Optimize queryset with related objects."""
        return super().get_queryset().select_related(
            'news', 'predicted_category', 'predicted_subcategory',
            'applied_rule', 'applied_model'
        )
    
    @extend_schema(
        summary="Accept classification",
        description="Accept a classification result and apply it to the news."
    )
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept classification result."""
        result = self.get_object()
        
        if result.is_accepted:
            return Response(
                {'message': 'Classification already accepted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result.accept_classification()
        
        return Response({'message': 'Classification accepted'})
    
    @extend_schema(
        summary="Reject classification",
        description="Reject a classification result."
    )
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject classification result."""
        result = self.get_object()
        
        # Mark as manual override
        result.is_manual_override = True
        result.save()
        
        return Response({'message': 'Classification rejected'})


@extend_schema_view(
    list=extend_schema(
        summary="List training data",
        description="Get a list of training data for machine learning models."
    ),
    create=extend_schema(
        summary="Create training data",
        description="Create new training data for model training."
    ),
)
class ClassificationTrainingDataViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing classification training data.
    """
    queryset = ClassificationTrainingData.objects.all()
    serializer_class = ClassificationTrainingDataSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'source', 'is_validated', 'used_in_training']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Optimize queryset."""
        return super().get_queryset().select_related('news', 'category', 'subcategory')
    
    @extend_schema(
        summary="Validate training data",
        description="Mark training data as validated and ready for use."
    )
    @action(detail=False, methods=['post'])
    def validate_batch(self, request):
        """Validate multiple training data entries."""
        ids = request.data.get('ids', [])
        
        if not ids:
            return Response(
                {'error': 'No IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated = ClassificationTrainingData.objects.filter(
            id__in=ids
        ).update(is_validated=True, used_in_training=True)
        
        return Response({
            'message': f'Validated {updated} training data entries'
        })


@extend_schema_view(
    list=extend_schema(
        summary="List classification statistics",
        description="Get classification statistics by date."
    ),
)
class ClassificationStatisticViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing classification statistics.
    """
    queryset = ClassificationStatistic.objects.all()
    serializer_class = ClassificationStatisticSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['date']
    ordering = ['-date']


class ClassificationAPIViewSet(viewsets.ViewSet):
    """
    API endpoints for classification operations.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Classify single news",
        description="Classify a single news article using specified method."
    )
    @action(detail=False, methods=['post'])
    def classify(self, request):
        """Classify a single news article."""
        serializer = NewsClassificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        news_id = serializer.validated_data['news_id']
        method = serializer.validated_data['method']
        force_reclassify = serializer.validated_data['force_reclassify']
        
        # Check if already processed
        from apps.news.models import News
        news = News.objects.get(id=news_id)
        
        if news.is_processed and not force_reclassify:
            return Response(
                {'error': 'News already processed. Use force_reclassify=true to reclassify.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start classification task
        task = classify_news.delay(news_id, method)
        
        return Response({
            'message': 'Classification started',
            'task_id': task.id,
            'news_id': str(news_id),
            'method': method
        })
    
    @extend_schema(
        summary="Bulk classify news",
        description="Classify multiple news articles in bulk."
    )
    @action(detail=False, methods=['post'])
    def bulk_classify(self, request):
        """Classify multiple news articles."""
        serializer = BulkClassificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        news_ids = [str(id) for id in serializer.validated_data['news_ids']]
        method = serializer.validated_data['method']
        
        # Start bulk classification task
        task = bulk_classify_news.delay(news_ids, method)
        
        return Response({
            'message': 'Bulk classification started',
            'task_id': task.id,
            'news_count': len(news_ids),
            'method': method
        })
    
    @extend_schema(
        summary="Get classification dashboard",
        description="Get aggregated classification statistics for dashboard."
    )
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get classification dashboard data."""
        # Get date range
        serializer = ClassificationStatsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        date_from = serializer.validated_data.get('date_from', timezone.now().date() - timezone.timedelta(days=7))
        date_to = serializer.validated_data.get('date_to', timezone.now().date())
        
        # Get statistics
        stats = ClassificationStatistic.objects.filter(
            date__range=[date_from, date_to]
        )
        
        # Aggregate data
        total_stats = stats.aggregate(
            total_classifications=models.Sum('total_classifications'),
            successful_classifications=models.Sum('successful_classifications'),
            avg_processing_time=Avg('avg_processing_time'),
            avg_confidence=Avg('avg_confidence_score')
        )
        
        # Method breakdown
        method_stats = stats.aggregate(
            keyword=models.Sum('keyword_classifications'),
            ml=models.Sum('ml_classifications'),
            hybrid=models.Sum('hybrid_classifications'),
            manual=models.Sum('manual_classifications')
        )
        
        # Recent activity
        recent_results = ClassificationResult.objects.filter(
            created_at__date__range=[date_from, date_to]
        ).order_by('-created_at')[:10]
        
        # Active rules and models
        active_rules = ClassificationRule.objects.filter(is_active=True).count()
        active_models = ClassificationModel.objects.filter(is_active=True, is_trained=True).count()
        
        return Response({
            'date_range': {'from': date_from, 'to': date_to},
            'overview': {
                'total_classifications': total_stats['total_classifications'] or 0,
                'successful_classifications': total_stats['successful_classifications'] or 0,
                'success_rate': (total_stats['successful_classifications'] or 0) / max(total_stats['total_classifications'] or 1, 1) * 100,
                'avg_processing_time': total_stats['avg_processing_time'] or 0,
                'avg_confidence': total_stats['avg_confidence'] or 0,
                'active_rules': active_rules,
                'active_models': active_models
            },
            'method_breakdown': method_stats,
            'recent_activity': ClassificationResultSerializer(recent_results, many=True).data,
            'daily_stats': ClassificationStatisticSerializer(stats, many=True).data
        })
    
    @extend_schema(
        summary="Generate training data",
        description="Generate training data from verified classifications."
    )
    @action(detail=False, methods=['post'])
    def generate_training_data(self, request):
        """Generate training data from verified classifications."""
        task = generate_training_data.delay()
        
        return Response({
            'message': 'Training data generation started',
            'task_id': task.id
        })
    
    @extend_schema(
        summary="Retrain all models",
        description="Retrain all active machine learning models."
    )
    @action(detail=False, methods=['post'])
    def retrain_models(self, request):
        """Retrain all active models."""
        task = retrain_models.delay()
        
        return Response({
            'message': 'Model retraining started',
            'task_id': task.id
        })