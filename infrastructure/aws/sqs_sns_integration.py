import boto3
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import uuid

logger = logging.getLogger(__name__)

class SQSSNSIntegration:
    """
    Integration layer to replace Redis/Celery with SQS/SNS for scalable message queuing
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        self.region_name = region_name
        self.sqs = boto3.client('sqs', region_name=region_name)
        self.sns = boto3.client('sns', region_name=region_name)
        
        # Queue URLs (should be loaded from environment or config)
        self.news_processing_queue_url = os.environ.get('NEWS_PROCESSING_QUEUE_URL')
        self.classification_queue_url = os.environ.get('CLASSIFICATION_QUEUE_URL')
        
        # SNS Topic ARNs
        self.notifications_topic_arn = os.environ.get('NOTIFICATIONS_TOPIC_ARN')
        self.urgent_news_topic_arn = os.environ.get('URGENT_NEWS_TOPIC_ARN')
    
    def send_news_for_processing(self, webhook_data: Dict[str, Any], priority: str = 'normal') -> bool:
        """
        Send news item to processing queue (replaces Celery task)
        
        Args:
            webhook_data: News data from webhook
            priority: Priority level (urgent, high, normal, low)
        
        Returns:
            bool: Success status
        """
        try:
            message_id = str(uuid.uuid4())
            
            # Prepare message
            message = {
                'id': message_id,
                'timestamp': datetime.utcnow().isoformat(),
                'news_data': webhook_data,
                'priority': priority,
                'source': 'webhook_receiver'
            }
            
            # Message attributes for filtering and priority
            message_attributes = {
                'priority': {
                    'StringValue': priority,
                    'DataType': 'String'
                },
                'message_type': {
                    'StringValue': 'news_processing',
                    'DataType': 'String'
                },
                'source': {
                    'StringValue': webhook_data.get('source', 'unknown'),
                    'DataType': 'String'
                }
            }
            
            # Send to SQS
            response = self.sqs.send_message(
                QueueUrl=self.news_processing_queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes=message_attributes,
                DelaySeconds=0 if priority in ['urgent', 'high'] else 5
            )
            
            logger.info(f"Sent news for processing: {message_id} - {response['MessageId']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending news for processing: {str(e)}")
            return False
    
    def send_for_classification(self, news_id: str, news_data: Dict[str, Any], priority: str = 'normal') -> bool:
        """
        Send news item to classification queue
        
        Args:
            news_id: News item ID
            news_data: News content for classification
            priority: Priority level
        
        Returns:
            bool: Success status
        """
        try:
            message_id = str(uuid.uuid4())
            
            # Prepare message
            message = {
                'id': message_id,
                'timestamp': datetime.utcnow().isoformat(),
                'news_id': news_id,
                'news_data': news_data,
                'priority': priority,
                'source': 'news_processor'
            }
            
            # Message attributes
            message_attributes = {
                'priority': {
                    'StringValue': priority,
                    'DataType': 'String'
                },
                'message_type': {
                    'StringValue': 'classification',
                    'DataType': 'String'
                },
                'news_id': {
                    'StringValue': news_id,
                    'DataType': 'String'
                }
            }
            
            # Send to classification queue
            response = self.sqs.send_message(
                QueueUrl=self.classification_queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes=message_attributes,
                DelaySeconds=0 if priority in ['urgent', 'high'] else 2
            )
            
            logger.info(f"Sent for classification: {news_id} - {response['MessageId']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending for classification: {str(e)}")
            return False
    
    def send_notification(self, notification_data: Dict[str, Any], is_urgent: bool = False) -> bool:
        """
        Send notification via SNS (replaces direct notification sending)
        
        Args:
            notification_data: Notification content
            is_urgent: Whether this is an urgent notification
        
        Returns:
            bool: Success status
        """
        try:
            message_id = str(uuid.uuid4())
            
            # Choose topic based on urgency
            topic_arn = self.urgent_news_topic_arn if is_urgent else self.notifications_topic_arn
            
            # Prepare message
            message = {
                'id': message_id,
                'timestamp': datetime.utcnow().isoformat(),
                'notification_data': notification_data,
                'is_urgent': is_urgent,
                'source': 'notification_sender'
            }
            
            # Message attributes
            message_attributes = {
                'urgency': {
                    'StringValue': 'urgent' if is_urgent else 'normal',
                    'DataType': 'String'
                },
                'message_type': {
                    'StringValue': 'notification',
                    'DataType': 'String'
                },
                'news_id': {
                    'StringValue': notification_data.get('news_id', ''),
                    'DataType': 'String'
                }
            }
            
            # Send to SNS
            response = self.sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message),
                Subject=f"JOTA News: {notification_data.get('title', 'Notification')}"[:100],
                MessageAttributes=message_attributes
            )
            
            logger.info(f"Sent notification: {message_id} - {response['MessageId']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False
    
    def get_queue_metrics(self, queue_url: str) -> Dict[str, Any]:
        """
        Get queue metrics for monitoring
        
        Args:
            queue_url: SQS queue URL
        
        Returns:
            Dict containing queue metrics
        """
        try:
            response = self.sqs.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=[
                    'ApproximateNumberOfMessages',
                    'ApproximateNumberOfMessagesNotVisible',
                    'ApproximateNumberOfMessagesDelayed'
                ]
            )
            
            attributes = response.get('Attributes', {})
            return {
                'messages_available': int(attributes.get('ApproximateNumberOfMessages', 0)),
                'messages_in_flight': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                'messages_delayed': int(attributes.get('ApproximateNumberOfMessagesDelayed', 0)),
                'queue_url': queue_url
            }
            
        except Exception as e:
            logger.error(f"Error getting queue metrics: {str(e)}")
            return {}
    
    def get_all_queue_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for all queues
        
        Returns:
            Dict containing all queue metrics
        """
        metrics = {}
        
        if self.news_processing_queue_url:
            metrics['news_processing'] = self.get_queue_metrics(self.news_processing_queue_url)
        
        if self.classification_queue_url:
            metrics['classification'] = self.get_queue_metrics(self.classification_queue_url)
        
        return metrics
    
    def purge_queue(self, queue_url: str) -> bool:
        """
        Purge a queue (for testing/admin purposes)
        
        Args:
            queue_url: SQS queue URL
        
        Returns:
            bool: Success status
        """
        try:
            self.sqs.purge_queue(QueueUrl=queue_url)
            logger.info(f"Purged queue: {queue_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error purging queue: {str(e)}")
            return False
    
    def create_sns_subscription(self, topic_arn: str, protocol: str, endpoint: str) -> Optional[str]:
        """
        Create SNS subscription for notifications
        
        Args:
            topic_arn: SNS topic ARN
            protocol: Subscription protocol (email, sms, lambda, etc.)
            endpoint: Subscription endpoint
        
        Returns:
            Subscription ARN if successful, None otherwise
        """
        try:
            response = self.sns.subscribe(
                TopicArn=topic_arn,
                Protocol=protocol,
                Endpoint=endpoint
            )
            
            subscription_arn = response['SubscriptionArn']
            logger.info(f"Created SNS subscription: {subscription_arn}")
            return subscription_arn
            
        except Exception as e:
            logger.error(f"Error creating SNS subscription: {str(e)}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health check for SQS/SNS integration
        
        Returns:
            Dict containing health status
        """
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {}
        }
        
        # Check SQS connectivity
        try:
            if self.news_processing_queue_url:
                self.get_queue_metrics(self.news_processing_queue_url)
            health_status['services']['sqs'] = 'healthy'
        except Exception as e:
            health_status['services']['sqs'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Check SNS connectivity
        try:
            if self.notifications_topic_arn:
                self.sns.get_topic_attributes(TopicArn=self.notifications_topic_arn)
            health_status['services']['sns'] = 'healthy'
        except Exception as e:
            health_status['services']['sns'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        return health_status

# Django integration adapter
class DjangoSQSSNSAdapter:
    """
    Django-specific adapter for SQS/SNS integration
    """
    
    def __init__(self):
        self.integration = SQSSNSIntegration()
    
    def replace_celery_task(self, task_name: str, *args, **kwargs):
        """
        Replace Celery task calls with SQS messages
        
        Args:
            task_name: Name of the original Celery task
            *args: Task arguments
            **kwargs: Task keyword arguments
        """
        if task_name == 'process_webhook_async':
            return self.integration.send_news_for_processing(
                webhook_data=args[0] if args else kwargs.get('webhook_data'),
                priority=kwargs.get('priority', 'normal')
            )
        
        elif task_name == 'classify_news_async':
            return self.integration.send_for_classification(
                news_id=args[0] if args else kwargs.get('news_id'),
                news_data=args[1] if len(args) > 1 else kwargs.get('news_data'),
                priority=kwargs.get('priority', 'normal')
            )
        
        elif task_name == 'send_notification_async':
            return self.integration.send_notification(
                notification_data=args[0] if args else kwargs.get('notification_data'),
                is_urgent=kwargs.get('is_urgent', False)
            )
        
        else:
            raise ValueError(f"Unknown task: {task_name}")
    
    def get_monitoring_data(self) -> Dict[str, Any]:
        """
        Get monitoring data for Django admin/dashboard
        
        Returns:
            Dict containing monitoring information
        """
        return {
            'queue_metrics': self.integration.get_all_queue_metrics(),
            'health_status': self.integration.health_check(),
            'timestamp': datetime.utcnow().isoformat()
        }

# Example usage in Django views
def example_django_usage():
    """
    Example of how to use the SQS/SNS integration in Django views
    """
    adapter = DjangoSQSSNSAdapter()
    
    # Replace Celery task call
    webhook_data = {
        'title': 'Breaking News',
        'content': 'Important news content...',
        'source': 'external_api'
    }
    
    # Instead of: process_webhook_async.delay(webhook_data)
    adapter.replace_celery_task('process_webhook_async', webhook_data, priority='high')
    
    # Get monitoring data for admin dashboard
    monitoring_data = adapter.get_monitoring_data()
    
    return monitoring_data