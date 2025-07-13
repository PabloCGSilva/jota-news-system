"""
Unit tests for classification models.
"""
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.classification.models import (
    ClassificationRule, ClassificationModel, ClassificationResult,
    ClassificationTrainingData, ClassificationStatistic
)


@pytest.mark.unit
class TestClassificationRule:
    """Tests for ClassificationRule model."""
    
    def test_create_classification_rule(self, db, category):
        """Test creating a classification rule."""
        rule = ClassificationRule.objects.create(
            name='Tech News Rule',
            description='Rule for classifying tech news',
            rule_type='keyword',
            target_category=category,
            keywords=['technology', 'software', 'programming'],
            patterns=[r'\b(AI|ML|artificial intelligence)\b'],
            weight=1.5,
            confidence_threshold=0.7,
            is_active=True,
            priority=100
        )
        
        assert rule.name == 'Tech News Rule'
        assert rule.rule_type == 'keyword'
        assert rule.target_category == category
        assert 'technology' in rule.keywords
        assert rule.weight == 1.5
        assert rule.confidence_threshold == 0.7
        assert rule.total_matches == 0
        assert rule.success_rate == 0
        assert str(rule) == f"Tech News Rule → {category.name}"
    
    def test_rule_increment_matches(self, db, classification_rule):
        """Test incrementing rule matches."""
        initial_matches = classification_rule.total_matches
        classification_rule.increment_matches()
        
        assert classification_rule.total_matches == initial_matches + 1
        assert classification_rule.last_used is not None
    
    def test_rule_increment_successful_classifications(self, db, classification_rule):
        """Test incrementing successful classifications."""
        initial_successful = classification_rule.successful_classifications
        classification_rule.increment_successful_classifications()
        
        assert classification_rule.successful_classifications == initial_successful + 1
    
    def test_rule_success_rate_calculation(self, db, classification_rule):
        """Test success rate calculation."""
        # Initially 0% success rate
        assert classification_rule.success_rate == 0
        
        # Add some matches and successes
        classification_rule.total_matches = 10
        classification_rule.successful_classifications = 8
        classification_rule.save()
        
        assert classification_rule.success_rate == 80.0
    
    def test_rule_unique_name(self, db, classification_rule):
        """Test rule name uniqueness."""
        with pytest.raises(Exception):  # IntegrityError or ValidationError
            ClassificationRule.objects.create(
                name=classification_rule.name,
                rule_type='pattern',
                target_category=classification_rule.target_category
            )


@pytest.mark.unit
class TestClassificationModel:
    """Tests for ClassificationModel model."""
    
    def test_create_classification_model(self, db):
        """Test creating a classification model."""
        model = ClassificationModel.objects.create(
            name='TF-IDF Model',
            description='TF-IDF with SVM model',
            model_type='tfidf',
            config={
                'max_features': 5000,
                'ngram_range': [1, 2]
            },
            is_active=False,
            is_trained=False
        )
        
        assert model.name == 'TF-IDF Model'
        assert model.model_type == 'tfidf'
        assert model.config['max_features'] == 5000
        assert model.is_trained is False
        assert model.total_predictions == 0
        assert str(model) == "TF-IDF Model (tfidf)"
    
    def test_model_increment_predictions(self, db):
        """Test incrementing model predictions."""
        model = ClassificationModel.objects.create(
            name='Test Model',
            model_type='nb'
        )
        
        initial_predictions = model.total_predictions
        model.increment_predictions()
        
        assert model.total_predictions == initial_predictions + 1
        assert model.last_used is not None


@pytest.mark.unit
class TestClassificationResult:
    """Tests for ClassificationResult model."""
    
    def test_create_classification_result(self, db, news, category, classification_rule):
        """Test creating a classification result."""
        result = ClassificationResult.objects.create(
            news=news,
            method='keyword',
            applied_rule=classification_rule,
            predicted_category=category,
            category_confidence=0.85,
            subcategory_confidence=0.0,
            urgency_confidence=0.1,
            prediction_details={
                'keyword_matches': ['test'],
                'confidence_breakdown': {'category': 0.85}
            },
            processing_time=0.05
        )
        
        assert result.news == news
        assert result.method == 'keyword'
        assert result.applied_rule == classification_rule
        assert result.predicted_category == category
        assert result.category_confidence == 0.85
        assert result.is_accepted is False
        assert str(result) == f"{news.title} → {category.name}"
    
    def test_accept_classification(self, db, news, category, classification_rule):
        """Test accepting a classification result."""
        result = ClassificationResult.objects.create(
            news=news,
            method='keyword',
            applied_rule=classification_rule,
            predicted_category=category,
            category_confidence=0.85,
            processing_time=0.05
        )
        
        # Accept the classification
        result.accept_classification()
        
        # Refresh from database
        result.refresh_from_db()
        news.refresh_from_db()
        
        assert result.is_accepted is True
        assert news.category == category
        assert news.category_confidence == 0.85
        assert news.is_processed is True


@pytest.mark.unit
class TestClassificationTrainingData:
    """Tests for ClassificationTrainingData model."""
    
    def test_create_training_data(self, db, news, category):
        """Test creating training data."""
        training_data = ClassificationTrainingData.objects.create(
            news=news,
            category=category,
            is_urgent=False,
            source='manual',
            confidence_score=1.0,
            is_validated=True,
            used_in_training=True
        )
        
        assert training_data.news == news
        assert training_data.category == category
        assert training_data.source == 'manual'
        assert training_data.confidence_score == 1.0
        assert training_data.is_validated is True
        assert str(training_data) == f"{news.title} → {category.name}"


@pytest.mark.unit
class TestClassificationStatistic:
    """Tests for ClassificationStatistic model."""
    
    def test_create_classification_statistic(self, db):
        """Test creating classification statistics."""
        today = timezone.now().date()
        
        statistic = ClassificationStatistic.objects.create(
            date=today,
            total_classifications=100,
            successful_classifications=85,
            failed_classifications=15,
            keyword_classifications=50,
            ml_classifications=30,
            hybrid_classifications=20,
            avg_processing_time=0.05,
            avg_confidence_score=0.78,
            category_breakdown={
                'technology': 40,
                'business': 30,
                'politics': 30
            }
        )
        
        assert statistic.date == today
        assert statistic.total_classifications == 100
        assert statistic.successful_classifications == 85
        assert statistic.success_rate == 85.0
        assert statistic.category_breakdown['technology'] == 40
        assert str(statistic) == f"Classification Statistics for {today}"
    
    def test_statistic_success_rate_calculation(self, db):
        """Test success rate calculation."""
        today = timezone.now().date()
        
        # Test with zero classifications
        statistic = ClassificationStatistic.objects.create(
            date=today,
            total_classifications=0,
            successful_classifications=0
        )
        assert statistic.success_rate == 0
        
        # Test with some classifications
        statistic.total_classifications = 50
        statistic.successful_classifications = 40
        statistic.save()
        
        assert statistic.success_rate == 80.0