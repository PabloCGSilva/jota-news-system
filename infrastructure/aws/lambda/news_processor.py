import json
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import os
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
sqs = boto3.client('sqs')
sns = boto3.client('sns')
rds = boto3.client('rds-data')
s3 = boto3.client('s3')

# Environment variables
CLASSIFICATION_QUEUE_URL = os.environ.get('CLASSIFICATION_QUEUE_URL')
NOTIFICATION_TOPIC_ARN = os.environ.get('NOTIFICATION_TOPIC_ARN')
DATABASE_SECRET_ARN = os.environ.get('DATABASE_SECRET_ARN')
DATABASE_CLUSTER_ARN = os.environ.get('DATABASE_CLUSTER_ARN')
S3_BUCKET = os.environ.get('S3_BUCKET')

class NewsProcessor:
    def __init__(self):
        self.correlation_id = str(uuid.uuid4())
        
    def process_news_item(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single news item from webhook"""
        try:
            logger.info(f"Processing news item: {news_data.get('title', 'Unknown')} - {self.correlation_id}")
            
            # Validate input data
            if not self._validate_news_data(news_data):
                raise ValueError("Invalid news data format")
            
            # Store news in database
            news_id = self._store_news_item(news_data)
            
            # Send to classification queue
            self._send_to_classification_queue(news_id, news_data)
            
            # If urgent, send immediate notification
            if news_data.get('is_urgent', False):
                self._send_urgent_notification(news_id, news_data)
            
            return {
                'status': 'success',
                'news_id': news_id,
                'correlation_id': self.correlation_id
            }
            
        except Exception as e:
            logger.error(f"Error processing news item: {str(e)} - {self.correlation_id}")
            raise
    
    def _validate_news_data(self, news_data: Dict[str, Any]) -> bool:
        """Validate required fields in news data"""
        required_fields = ['title', 'content', 'source']
        return all(field in news_data for field in required_fields)
    
    def _store_news_item(self, news_data: Dict[str, Any]) -> str:
        """Store news item in RDS Aurora Serverless"""
        try:
            news_id = str(uuid.uuid4())
            
            # Execute SQL using RDS Data API
            response = rds.execute_statement(
                secretArn=DATABASE_SECRET_ARN,
                resourceArn=DATABASE_CLUSTER_ARN,
                database='jota_news',
                sql="""
                    INSERT INTO news_news (
                        id, title, content, source, author, 
                        created_at, updated_at, is_urgent, is_processed,
                        correlation_id
                    ) VALUES (
                        :id, :title, :content, :source, :author,
                        :created_at, :updated_at, :is_urgent, :is_processed,
                        :correlation_id
                    )
                """,
                parameters=[
                    {'name': 'id', 'value': {'stringValue': news_id}},
                    {'name': 'title', 'value': {'stringValue': news_data['title']}},
                    {'name': 'content', 'value': {'stringValue': news_data['content']}},
                    {'name': 'source', 'value': {'stringValue': news_data['source']}},
                    {'name': 'author', 'value': {'stringValue': news_data.get('author', 'Unknown')}},
                    {'name': 'created_at', 'value': {'stringValue': datetime.utcnow().isoformat()}},
                    {'name': 'updated_at', 'value': {'stringValue': datetime.utcnow().isoformat()}},
                    {'name': 'is_urgent', 'value': {'booleanValue': news_data.get('is_urgent', False)}},
                    {'name': 'is_processed', 'value': {'booleanValue': False}},
                    {'name': 'correlation_id', 'value': {'stringValue': self.correlation_id}}
                ]
            )
            
            logger.info(f"Stored news item with ID: {news_id}")
            return news_id
            
        except Exception as e:
            logger.error(f"Error storing news item: {str(e)}")
            raise
    
    def _send_to_classification_queue(self, news_id: str, news_data: Dict[str, Any]):
        """Send news to classification queue for processing"""
        try:
            message = {
                'news_id': news_id,
                'title': news_data['title'],
                'content': news_data['content'],
                'correlation_id': self.correlation_id,
                'priority': 'high' if news_data.get('is_urgent', False) else 'normal'
            }
            
            # Send to SQS queue with message attributes for priority
            sqs.send_message(
                QueueUrl=CLASSIFICATION_QUEUE_URL,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'priority': {
                        'StringValue': message['priority'],
                        'DataType': 'String'
                    },
                    'correlation_id': {
                        'StringValue': self.correlation_id,
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Sent news {news_id} to classification queue")
            
        except Exception as e:
            logger.error(f"Error sending to classification queue: {str(e)}")
            raise
    
    def _send_urgent_notification(self, news_id: str, news_data: Dict[str, Any]):
        """Send urgent notification via SNS"""
        try:
            message = {
                'type': 'urgent_news',
                'news_id': news_id,
                'title': news_data['title'],
                'correlation_id': self.correlation_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            sns.publish(
                TopicArn=NOTIFICATION_TOPIC_ARN,
                Message=json.dumps(message),
                Subject=f"Urgent News: {news_data['title'][:50]}...",
                MessageAttributes={
                    'type': {
                        'StringValue': 'urgent_news',
                        'DataType': 'String'
                    },
                    'correlation_id': {
                        'StringValue': self.correlation_id,
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Sent urgent notification for news {news_id}")
            
        except Exception as e:
            logger.error(f"Error sending urgent notification: {str(e)}")
            raise

def lambda_handler(event, context):
    """Main Lambda handler for processing news items"""
    try:
        processor = NewsProcessor()
        
        # Handle SQS event (batch processing)
        if 'Records' in event:
            results = []
            for record in event['Records']:
                if record.get('eventSource') == 'aws:sqs':
                    # Process SQS message
                    message_body = json.loads(record['body'])
                    result = processor.process_news_item(message_body)
                    results.append(result)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Batch processing completed',
                    'results': results
                })
            }
        
        # Handle direct invocation
        elif 'news_data' in event:
            result = processor.process_news_item(event['news_data'])
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid event format'})
            }
            
    except Exception as e:
        logger.error(f"Lambda execution error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'correlation_id': getattr(processor, 'correlation_id', 'unknown')
            })
        }

# Health check function
def health_check_handler(event, context):
    """Health check endpoint for Lambda"""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    }