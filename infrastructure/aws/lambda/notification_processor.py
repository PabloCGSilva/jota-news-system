import json
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
import uuid
import requests
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
sqs = boto3.client('sqs')
sns = boto3.client('sns')
rds = boto3.client('rds-data')
s3 = boto3.client('s3')
ses = boto3.client('ses')

# Environment variables
DATABASE_SECRET_ARN = os.environ.get('DATABASE_SECRET_ARN')
DATABASE_CLUSTER_ARN = os.environ.get('DATABASE_CLUSTER_ARN')
WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
SES_REGION = os.environ.get('SES_REGION', 'us-east-1')

class NotificationProcessor:
    def __init__(self):
        self.correlation_id = str(uuid.uuid4())
        
    def process_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process notification based on type and channel"""
        try:
            notification_type = notification_data.get('type', 'news_update')
            news_id = notification_data.get('news_id')
            
            logger.info(f"Processing notification: {notification_type} for news {news_id} - {self.correlation_id}")
            
            # Get subscriptions for this notification type
            subscriptions = self._get_active_subscriptions(notification_type, news_id)
            
            if not subscriptions:
                logger.info(f"No active subscriptions found for {notification_type}")
                return {
                    'status': 'success',
                    'message': 'No active subscriptions',
                    'correlation_id': self.correlation_id
                }
            
            # Process each subscription
            results = []
            for subscription in subscriptions:
                try:
                    result = self._send_notification(subscription, notification_data)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error sending notification to {subscription['id']}: {str(e)}")
                    results.append({
                        'subscription_id': subscription['id'],
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Store notification results
            self._store_notification_results(notification_data, results)
            
            return {
                'status': 'success',
                'notifications_sent': len([r for r in results if r['status'] == 'success']),
                'notifications_failed': len([r for r in results if r['status'] == 'failed']),
                'results': results,
                'correlation_id': self.correlation_id
            }
            
        except Exception as e:
            logger.error(f"Error processing notification: {str(e)} - {self.correlation_id}")
            raise
    
    def _get_active_subscriptions(self, notification_type: str, news_id: str) -> List[Dict[str, Any]]:
        """Get active subscriptions for notification type"""
        try:
            # Get news details for filtering
            news_details = self._get_news_details(news_id)
            
            # Base query for active subscriptions
            sql = """
                SELECT 
                    s.id, s.user_id, s.channel_id, s.destination,
                    s.min_priority, s.categories, s.keywords,
                    c.name as channel_name, c.provider, c.config
                FROM notifications_notificationsubscription s
                JOIN notifications_notificationchannel c ON s.channel_id = c.id
                WHERE s.is_active = true AND c.is_active = true
            """
            
            # Add filters based on notification type
            if notification_type == 'urgent_news':
                sql += " AND s.min_priority IN ('high', 'urgent')"
            elif notification_type == 'news_classified':
                sql += " AND s.min_priority IN ('medium', 'high', 'urgent')"
            
            response = rds.execute_statement(
                secretArn=DATABASE_SECRET_ARN,
                resourceArn=DATABASE_CLUSTER_ARN,
                database='jota_news',
                sql=sql
            )
            
            subscriptions = []
            for record in response.get('records', []):
                subscription = {
                    'id': record[0]['stringValue'],
                    'user_id': record[1]['stringValue'],
                    'channel_id': record[2]['stringValue'],
                    'destination': record[3]['stringValue'],
                    'min_priority': record[4]['stringValue'],
                    'categories': record[5]['stringValue'].split(',') if record[5].get('stringValue') else [],
                    'keywords': record[6]['stringValue'].split(',') if record[6].get('stringValue') else [],
                    'channel_name': record[7]['stringValue'],
                    'provider': record[8]['stringValue'],
                    'config': json.loads(record[9]['stringValue']) if record[9].get('stringValue') else {}
                }
                
                # Apply content-based filtering
                if self._should_send_notification(subscription, news_details):
                    subscriptions.append(subscription)
            
            logger.info(f"Found {len(subscriptions)} matching subscriptions")
            return subscriptions
            
        except Exception as e:
            logger.error(f"Error getting subscriptions: {str(e)}")
            return []
    
    def _get_news_details(self, news_id: str) -> Dict[str, Any]:
        """Get news details for filtering"""
        try:
            response = rds.execute_statement(
                secretArn=DATABASE_SECRET_ARN,
                resourceArn=DATABASE_CLUSTER_ARN,
                database='jota_news',
                sql="""
                    SELECT 
                        n.id, n.title, n.content, n.category_id, n.is_urgent,
                        c.name as category_name
                    FROM news_news n
                    LEFT JOIN news_category c ON n.category_id = c.id
                    WHERE n.id = :news_id
                """,
                parameters=[
                    {'name': 'news_id', 'value': {'stringValue': news_id}}
                ]
            )
            
            if not response.get('records'):
                return {}
            
            record = response['records'][0]
            return {
                'id': record[0]['stringValue'],
                'title': record[1]['stringValue'],
                'content': record[2]['stringValue'],
                'category_id': record[3]['stringValue'] if record[3].get('stringValue') else None,
                'is_urgent': record[4]['booleanValue'],
                'category_name': record[5]['stringValue'] if record[5].get('stringValue') else None
            }
            
        except Exception as e:
            logger.error(f"Error getting news details: {str(e)}")
            return {}
    
    def _should_send_notification(self, subscription: Dict[str, Any], news_details: Dict[str, Any]) -> bool:
        """Check if notification should be sent based on subscription filters"""
        try:
            # Check category filter
            if subscription['categories'] and news_details.get('category_id'):
                if news_details['category_id'] not in subscription['categories']:
                    return False
            
            # Check keyword filter
            if subscription['keywords']:
                text = f"{news_details.get('title', '')} {news_details.get('content', '')}".lower()
                if not any(keyword.lower() in text for keyword in subscription['keywords']):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking notification filters: {str(e)}")
            return False
    
    def _send_notification(self, subscription: Dict[str, Any], notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification via appropriate channel"""
        try:
            provider = subscription['provider']
            
            if provider == 'email':
                return self._send_email_notification(subscription, notification_data)
            elif provider == 'slack':
                return self._send_slack_notification(subscription, notification_data)
            elif provider == 'sms':
                return self._send_sms_notification(subscription, notification_data)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
                
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            raise
    
    # WhatsApp notification method removed - external META Business API dependency not needed
    
    def _send_email_notification(self, subscription: Dict[str, Any], notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email notification"""
        try:
            news_id = notification_data.get('news_id')
            notification_type = notification_data.get('type', 'news_update')
            
            # Get news details
            news_details = self._get_news_details(news_id)
            
            # Format email
            subject = f"JOTA News: {news_details.get('title', 'News Update')}"
            if notification_type == 'urgent_news':
                subject = f"🚨 URGENT - {subject}"
            
            body = f"""
            <html>
            <body>
                <h2>{news_details.get('title', 'News Update')}</h2>
                <p><strong>Category:</strong> {news_details.get('category_name', 'Uncategorized')}</p>
                <p><strong>Content:</strong></p>
                <p>{news_details.get('content', '')}</p>
                <hr>
                <p><small>This is an automated message from JOTA News System.</small></p>
            </body>
            </html>
            """
            
            # Send email via SES
            ses.send_email(
                Source='noreply@jota.news',
                Destination={
                    'ToAddresses': [subscription['destination']]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': body,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )
            
            logger.info(f"Email notification sent to {subscription['destination']}")
            return {
                'subscription_id': subscription['id'],
                'status': 'success',
                'provider': 'email',
                'destination': subscription['destination']
            }
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            raise
    
    def _send_slack_notification(self, subscription: Dict[str, Any], notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send Slack notification"""
        try:
            news_id = notification_data.get('news_id')
            notification_type = notification_data.get('type', 'news_update')
            
            # Get news details
            news_details = self._get_news_details(news_id)
            
            # Format Slack message
            emoji = "🚨" if notification_type == 'urgent_news' else "📰"
            color = "danger" if notification_type == 'urgent_news' else "good"
            
            slack_message = {
                "text": f"{emoji} News Update from JOTA",
                "attachments": [
                    {
                        "color": color,
                        "title": news_details.get('title', 'News Update'),
                        "text": news_details.get('content', '')[:500] + "...",
                        "fields": [
                            {
                                "title": "Category",
                                "value": news_details.get('category_name', 'Uncategorized'),
                                "short": True
                            },
                            {
                                "title": "Type",
                                "value": "Urgent" if notification_type == 'urgent_news' else "Regular",
                                "short": True
                            }
                        ],
                        "footer": "JOTA News System",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            # Send to Slack webhook
            response = requests.post(
                subscription['destination'],
                json=slack_message,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Slack notification sent to {subscription['destination']}")
                return {
                    'subscription_id': subscription['id'],
                    'status': 'success',
                    'provider': 'slack',
                    'destination': subscription['destination']
                }
            else:
                raise Exception(f"Slack webhook error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
            raise
    
    def _send_sms_notification(self, subscription: Dict[str, Any], notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send SMS notification"""
        try:
            news_id = notification_data.get('news_id')
            notification_type = notification_data.get('type', 'news_update')
            
            # Get news details
            news_details = self._get_news_details(news_id)
            
            # Format SMS message (160 character limit)
            prefix = "🚨 URGENT: " if notification_type == 'urgent_news' else "📰 "
            title = news_details.get('title', 'News Update')
            
            # Calculate available space for title
            available_space = 160 - len(prefix) - len(" - JOTA News")
            if len(title) > available_space:
                title = title[:available_space-3] + "..."
            
            message = f"{prefix}{title} - JOTA News"
            
            # Send SMS via SNS
            sns.publish(
                PhoneNumber=subscription['destination'],
                Message=message
            )
            
            logger.info(f"SMS notification sent to {subscription['destination']}")
            return {
                'subscription_id': subscription['id'],
                'status': 'success',
                'provider': 'sms',
                'destination': subscription['destination']
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {str(e)}")
            raise
    
    def _store_notification_results(self, notification_data: Dict[str, Any], results: List[Dict[str, Any]]):
        """Store notification results in database"""
        try:
            for result in results:
                notification_id = str(uuid.uuid4())
                
                rds.execute_statement(
                    secretArn=DATABASE_SECRET_ARN,
                    resourceArn=DATABASE_CLUSTER_ARN,
                    database='jota_news',
                    sql="""
                        INSERT INTO notifications_notification (
                            id, subscription_id, news_id, status, provider,
                            destination, sent_at, correlation_id, metadata
                        ) VALUES (
                            :id, :subscription_id, :news_id, :status, :provider,
                            :destination, :sent_at, :correlation_id, :metadata
                        )
                    """,
                    parameters=[
                        {'name': 'id', 'value': {'stringValue': notification_id}},
                        {'name': 'subscription_id', 'value': {'stringValue': result.get('subscription_id', '')}},
                        {'name': 'news_id', 'value': {'stringValue': notification_data.get('news_id', '')}},
                        {'name': 'status', 'value': {'stringValue': result.get('status', 'unknown')}},
                        {'name': 'provider', 'value': {'stringValue': result.get('provider', 'unknown')}},
                        {'name': 'destination', 'value': {'stringValue': result.get('destination', '')}},
                        {'name': 'sent_at', 'value': {'stringValue': datetime.utcnow().isoformat()}},
                        {'name': 'correlation_id', 'value': {'stringValue': self.correlation_id}},
                        {'name': 'metadata', 'value': {'stringValue': json.dumps(result)}}
                    ]
                )
            
            logger.info(f"Stored {len(results)} notification results")
            
        except Exception as e:
            logger.error(f"Error storing notification results: {str(e)}")
            raise

def lambda_handler(event, context):
    """Main Lambda handler for notification processing"""
    try:
        processor = NotificationProcessor()
        
        # Handle SNS event
        if 'Records' in event:
            results = []
            for record in event['Records']:
                if record.get('EventSource') == 'aws:sns':
                    # Process SNS message
                    message = json.loads(record['Sns']['Message'])
                    result = processor.process_notification(message)
                    results.append(result)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Notification processing completed',
                    'results': results
                })
            }
        
        # Handle direct invocation
        elif 'notification_data' in event:
            result = processor.process_notification(event['notification_data'])
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