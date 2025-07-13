"""
Celery tasks for news classification.
"""
import logging
import time
from celery import shared_task
from django.utils import timezone
from django.db import transaction

from .classifier import classifier
from .models import (
    ClassificationRule, ClassificationModel, ClassificationResult,
    ClassificationTrainingData, ClassificationStatistic
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def classify_news(self, news_id, method='hybrid'):
    """
    Classify a news article.
    """
    try:
        from apps.news.models import News, Category, Subcategory
        
        # Get news
        news = News.objects.get(id=news_id)
        
        if news.is_processed:
            return {'status': 'already_processed', 'news_id': str(news_id)}
        
        start_time = time.time()
        
        # Classify using the classifier engine
        result = classifier.classify_news(news.title, news.content, method)
        
        # Get category and subcategory objects
        category = None
        subcategory = None
        
        if result['category']:
            try:
                category = Category.objects.get(
                    name__iexact=result['category'],
                    is_active=True
                )
            except Category.DoesNotExist:
                # Create category if it doesn't exist
                category = Category.objects.create(
                    name=result['category'].title(),
                    slug=result['category'].lower().replace(' ', '-'),
                    description=f"Auto-created category: {result['category']}"
                )
        
        if result['subcategory'] and category:
            try:
                subcategory = Subcategory.objects.get(
                    name__iexact=result['subcategory'],
                    category=category,
                    is_active=True
                )
            except Subcategory.DoesNotExist:
                # Create subcategory if it doesn't exist
                subcategory = Subcategory.objects.create(
                    name=result['subcategory'].title(),
                    slug=result['subcategory'].lower().replace(' ', '-'),
                    category=category,
                    description=f"Auto-created subcategory: {result['subcategory']}"
                )
        
        # Create classification result
        with transaction.atomic():
            classification_result = ClassificationResult.objects.create(
                news=news,
                method=result['method'],
                predicted_category=category or Category.objects.get(name='Geral'),
                predicted_subcategory=subcategory,
                category_confidence=result['category_confidence'],
                subcategory_confidence=result['subcategory_confidence'],
                urgency_confidence=result['urgency_confidence'],
                prediction_details=result['details'],
                processing_time=result['processing_time']
            )
            
            # Auto-accept high-confidence classifications
            if result['category_confidence'] >= 0.8:
                classification_result.accept_classification()
            else:
                # Update news with classification but don't mark as processed
                news.category = classification_result.predicted_category
                news.subcategory = classification_result.predicted_subcategory
                news.category_confidence = result['category_confidence']
                news.subcategory_confidence = result['subcategory_confidence']
                news.urgency_confidence = result['urgency_confidence']
                
                # Set urgency based on classification
                if result['urgency_confidence'] >= 0.6:
                    news.is_urgent = True
                
                news.save()
        
        # Create processing log
        from apps.news.models import NewsProcessingLog
        NewsProcessingLog.objects.create(
            news=news,
            stage='classification',
            status='success',
            message=f"Classified as {category.name if category else 'Unknown'} with {result['category_confidence']:.2f} confidence",
            processing_time=result['processing_time']
        )
        
        logger.info(f"Successfully classified news {news_id}: {category.name if category else 'Unknown'}")
        
        return {
            'status': 'success',
            'news_id': str(news_id),
            'category': category.name if category else None,
            'subcategory': subcategory.name if subcategory else None,
            'confidence': result['category_confidence'],
            'processing_time': result['processing_time']
        }
        
    except Exception as exc:
        logger.error(f"Error classifying news {news_id}: {str(exc)}", exc_info=True)
        
        # Create error log
        try:
            from apps.news.models import News, NewsProcessingLog
            news = News.objects.get(id=news_id)
            NewsProcessingLog.objects.create(
                news=news,
                stage='classification',
                status='error',
                message=f"Classification failed: {str(exc)}",
                processing_time=0.0
            )
        except:
            pass
        
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=3)
def train_classification_model(self, model_id):
    """
    Train a classification model.
    """
    try:
        model = ClassificationModel.objects.get(id=model_id)
        
        # Get training data
        training_data = ClassificationTrainingData.objects.filter(
            is_validated=True,
            used_in_training=True
        ).select_related('news', 'category')
        
        if training_data.count() < 50:
            return {
                'status': 'error',
                'error': 'Insufficient training data (minimum 50 samples required)'
            }
        
        # Prepare training data
        texts = []
        labels = []
        
        for data in training_data:
            texts.append((data.news.title, data.news.content))
            labels.append(data.category.name.lower())
        
        # Train model
        training_result = classifier.train_model(texts, labels)
        
        if 'error' in training_result:
            return {
                'status': 'error',
                'error': training_result['error']
            }
        
        # Save model
        model_path = f"/shared/models/{model.id}.pkl"
        if classifier.save_model(model_path):
            model.model_file_path = model_path
            model.is_trained = True
            model.last_trained = timezone.now()
            model.training_data_count = len(texts)
            model.training_accuracy = training_result['accuracy']
            model.validation_accuracy = training_result['accuracy']  # Same for now
            model.save()
            
            return {
                'status': 'success',
                'model_id': str(model_id),
                'accuracy': training_result['accuracy'],
                'training_samples': len(texts)
            }
        else:
            return {
                'status': 'error',
                'error': 'Failed to save model'
            }
            
    except Exception as exc:
        logger.error(f"Error training model {model_id}: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def update_classification_statistics(self):
    """
    Update daily classification statistics.
    """
    try:
        today = timezone.now().date()
        
        # Get all classifications for today
        today_results = ClassificationResult.objects.filter(
            created_at__date=today
        )
        
        # Calculate statistics
        total_classifications = today_results.count()
        successful_classifications = today_results.filter(is_accepted=True).count()
        failed_classifications = total_classifications - successful_classifications
        
        # Method breakdown
        keyword_classifications = today_results.filter(method='keyword').count()
        ml_classifications = today_results.filter(method='ml').count()
        hybrid_classifications = today_results.filter(method='hybrid').count()
        manual_classifications = today_results.filter(method='manual').count()
        
        # Performance metrics
        avg_processing_time = today_results.aggregate(
            avg=models.Avg('processing_time')
        )['avg'] or 0.0
        
        avg_confidence_score = today_results.aggregate(
            avg=models.Avg('category_confidence')
        )['avg'] or 0.0
        
        # Category breakdown
        category_breakdown = {}
        for result in today_results.select_related('predicted_category'):
            category_name = result.predicted_category.name
            category_breakdown[category_name] = category_breakdown.get(category_name, 0) + 1
        
        # Update or create statistics
        statistic, created = ClassificationStatistic.objects.update_or_create(
            date=today,
            defaults={
                'total_classifications': total_classifications,
                'successful_classifications': successful_classifications,
                'failed_classifications': failed_classifications,
                'keyword_classifications': keyword_classifications,
                'ml_classifications': ml_classifications,
                'hybrid_classifications': hybrid_classifications,
                'manual_classifications': manual_classifications,
                'avg_processing_time': avg_processing_time,
                'avg_confidence_score': avg_confidence_score,
                'category_breakdown': category_breakdown,
            }
        )
        
        action = 'created' if created else 'updated'
        logger.info(f"Classification statistics {action} for {today}")
        
        return {
            'status': 'success',
            'date': str(today),
            'total_classifications': total_classifications,
            'success_rate': statistic.success_rate,
            'action': action
        }
        
    except Exception as exc:
        logger.error(f"Error updating classification statistics: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def bulk_classify_news(self, news_ids, method='hybrid'):
    """
    Classify multiple news articles in bulk.
    """
    try:
        processed_count = 0
        errors = []
        
        for news_id in news_ids:
            try:
                result = classify_news.delay(news_id, method)
                processed_count += 1
            except Exception as e:
                errors.append(f"Error classifying news {news_id}: {str(e)}")
        
        logger.info(f"Bulk classification initiated for {processed_count} news articles")
        
        return {
            'status': 'success',
            'processed_count': processed_count,
            'errors': errors
        }
        
    except Exception as exc:
        logger.error(f"Error in bulk classification: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def retrain_models(self):
    """
    Retrain all active models with new data.
    """
    try:
        active_models = ClassificationModel.objects.filter(is_active=True)
        
        retrained_count = 0
        errors = []
        
        for model in active_models:
            try:
                result = train_classification_model.delay(model.id)
                retrained_count += 1
            except Exception as e:
                errors.append(f"Error retraining model {model.id}: {str(e)}")
        
        logger.info(f"Retraining initiated for {retrained_count} models")
        
        return {
            'status': 'success',
            'retrained_count': retrained_count,
            'errors': errors
        }
        
    except Exception as exc:
        logger.error(f"Error in model retraining: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def cleanup_old_classification_results(self, days=90):
    """
    Clean up old classification results.
    """
    try:
        from django.utils import timezone
        
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Delete old results
        deleted_count = ClassificationResult.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old classification results")
        
        return {
            'status': 'success',
            'deleted_count': deleted_count
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up classification results: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_training_data(self):
    """
    Generate training data from verified classifications.
    """
    try:
        from apps.news.models import News
        
        # Get news with high-confidence classifications
        high_confidence_news = News.objects.filter(
            category_confidence__gte=0.9,
            is_processed=True
        ).exclude(
            training_data__isnull=False
        )
        
        created_count = 0
        
        for news in high_confidence_news:
            training_data, created = ClassificationTrainingData.objects.get_or_create(
                news=news,
                defaults={
                    'category': news.category,
                    'subcategory': news.subcategory,
                    'is_urgent': news.is_urgent,
                    'source': 'verified',
                    'confidence_score': news.category_confidence,
                    'is_validated': True,
                    'used_in_training': True
                }
            )
            
            if created:
                created_count += 1
        
        logger.info(f"Generated {created_count} training data samples")
        
        return {
            'status': 'success',
            'created_count': created_count
        }
        
    except Exception as exc:
        logger.error(f"Error generating training data: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)