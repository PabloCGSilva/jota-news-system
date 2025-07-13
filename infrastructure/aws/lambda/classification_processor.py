import json
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
import uuid
import re
from collections import Counter

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
sqs = boto3.client('sqs')
sns = boto3.client('sns')
rds = boto3.client('rds-data')
s3 = boto3.client('s3')

# Environment variables
NOTIFICATION_TOPIC_ARN = os.environ.get('NOTIFICATION_TOPIC_ARN')
DATABASE_SECRET_ARN = os.environ.get('DATABASE_SECRET_ARN')
DATABASE_CLUSTER_ARN = os.environ.get('DATABASE_CLUSTER_ARN')
S3_BUCKET = os.environ.get('S3_BUCKET')

class NewsClassifier:
    def __init__(self):
        self.correlation_id = str(uuid.uuid4())
        self.categories = self._load_categories()
        self.classification_rules = self._load_classification_rules()
        
    def classify_news(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """Classify news item using rule-based and ML approaches"""
        try:
            news_id = news_data['news_id']
            title = news_data['title']
            content = news_data['content']
            
            logger.info(f"Classifying news: {news_id} - {self.correlation_id}")
            
            # Rule-based classification
            rule_results = self._classify_by_rules(title, content)
            
            # Keyword-based classification
            keyword_results = self._classify_by_keywords(title, content)
            
            # Combine results and determine final classification
            final_classification = self._combine_classifications(rule_results, keyword_results)
            
            # Store classification results
            self._store_classification_results(news_id, final_classification)
            
            # Update news item with classification
            self._update_news_classification(news_id, final_classification)
            
            # Send notification if high confidence classification
            if final_classification['confidence'] > 0.8:
                self._send_classification_notification(news_id, final_classification)
            
            return {
                'status': 'success',
                'news_id': news_id,
                'classification': final_classification,
                'correlation_id': self.correlation_id
            }
            
        except Exception as e:
            logger.error(f"Error classifying news: {str(e)} - {self.correlation_id}")
            raise
    
    def _load_categories(self) -> Dict[str, Dict[str, Any]]:
        """Load categories from database"""
        try:
            response = rds.execute_statement(
                secretArn=DATABASE_SECRET_ARN,
                resourceArn=DATABASE_CLUSTER_ARN,
                database='jota_news',
                sql="""
                    SELECT id, name, keywords, description
                    FROM news_category
                    WHERE is_active = true
                """
            )
            
            categories = {}
            for record in response.get('records', []):
                category_id = record[0]['stringValue']
                name = record[1]['stringValue']
                keywords = record[2]['stringValue'] if record[2].get('stringValue') else ''
                description = record[3]['stringValue'] if record[3].get('stringValue') else ''
                
                categories[category_id] = {
                    'name': name,
                    'keywords': keywords.split(',') if keywords else [],
                    'description': description
                }
            
            logger.info(f"Loaded {len(categories)} categories")
            return categories
            
        except Exception as e:
            logger.error(f"Error loading categories: {str(e)}")
            return {}
    
    def _load_classification_rules(self) -> List[Dict[str, Any]]:
        """Load classification rules from database"""
        try:
            response = rds.execute_statement(
                secretArn=DATABASE_SECRET_ARN,
                resourceArn=DATABASE_CLUSTER_ARN,
                database='jota_news',
                sql="""
                    SELECT id, name, pattern, category_id, confidence_score, is_active
                    FROM classification_classificationrule
                    WHERE is_active = true
                    ORDER BY confidence_score DESC
                """
            )
            
            rules = []
            for record in response.get('records', []):
                rule = {
                    'id': record[0]['stringValue'],
                    'name': record[1]['stringValue'],
                    'pattern': record[2]['stringValue'],
                    'category_id': record[3]['stringValue'],
                    'confidence_score': float(record[4]['doubleValue']),
                    'is_active': record[5]['booleanValue']
                }
                rules.append(rule)
            
            logger.info(f"Loaded {len(rules)} classification rules")
            return rules
            
        except Exception as e:
            logger.error(f"Error loading classification rules: {str(e)}")
            return []
    
    def _classify_by_rules(self, title: str, content: str) -> Dict[str, Any]:
        """Classify using regex patterns and rules"""
        text = f"{title} {content}".lower()
        matches = []
        
        for rule in self.classification_rules:
            try:
                pattern = rule['pattern']
                if re.search(pattern, text, re.IGNORECASE):
                    matches.append({
                        'rule_id': rule['id'],
                        'rule_name': rule['name'],
                        'category_id': rule['category_id'],
                        'confidence': rule['confidence_score'],
                        'method': 'rule-based'
                    })
            except re.error as e:
                logger.warning(f"Invalid regex pattern in rule {rule['id']}: {e}")
                continue
        
        # Return highest confidence match
        if matches:
            best_match = max(matches, key=lambda x: x['confidence'])
            return best_match
        
        return {'confidence': 0.0, 'method': 'rule-based'}
    
    def _classify_by_keywords(self, title: str, content: str) -> Dict[str, Any]:
        """Classify using keyword matching"""
        text = f"{title} {content}".lower()
        category_scores = {}
        
        for category_id, category_data in self.categories.items():
            score = 0
            matched_keywords = []
            
            for keyword in category_data['keywords']:
                keyword_lower = keyword.lower().strip()
                if keyword_lower in text:
                    # Weight title keywords higher
                    if keyword_lower in title.lower():
                        score += 2
                    else:
                        score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                category_scores[category_id] = {
                    'score': score,
                    'matched_keywords': matched_keywords,
                    'category_name': category_data['name']
                }
        
        if category_scores:
            # Find category with highest score
            best_category = max(category_scores.items(), key=lambda x: x[1]['score'])
            category_id, data = best_category
            
            # Normalize confidence score (0-1)
            max_possible_score = len(self.categories[category_id]['keywords']) * 2
            confidence = min(data['score'] / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
            
            return {
                'category_id': category_id,
                'category_name': data['category_name'],
                'confidence': confidence,
                'matched_keywords': data['matched_keywords'],
                'method': 'keyword-based'
            }
        
        return {'confidence': 0.0, 'method': 'keyword-based'}
    
    def _combine_classifications(self, rule_results: Dict[str, Any], keyword_results: Dict[str, Any]) -> Dict[str, Any]:
        """Combine rule-based and keyword-based classifications"""
        rule_confidence = rule_results.get('confidence', 0.0)
        keyword_confidence = keyword_results.get('confidence', 0.0)
        
        # Use rule-based if high confidence, otherwise use keyword-based
        if rule_confidence > 0.7:
            return rule_results
        elif keyword_confidence > 0.5:
            return keyword_results
        elif rule_confidence > keyword_confidence:
            return rule_results
        else:
            return keyword_results if keyword_confidence > 0 else {
                'confidence': 0.0,
                'method': 'unclassified',
                'category_id': None
            }
    
    def _store_classification_results(self, news_id: str, classification: Dict[str, Any]):
        """Store classification results in database"""
        try:
            rds.execute_statement(
                secretArn=DATABASE_SECRET_ARN,
                resourceArn=DATABASE_CLUSTER_ARN,
                database='jota_news',
                sql="""
                    INSERT INTO classification_classificationresult (
                        id, news_id, category_id, confidence_score, method,
                        metadata, created_at, correlation_id
                    ) VALUES (
                        :id, :news_id, :category_id, :confidence_score, :method,
                        :metadata, :created_at, :correlation_id
                    )
                """,
                parameters=[
                    {'name': 'id', 'value': {'stringValue': str(uuid.uuid4())}},
                    {'name': 'news_id', 'value': {'stringValue': news_id}},
                    {'name': 'category_id', 'value': {'stringValue': classification.get('category_id', '')}},
                    {'name': 'confidence_score', 'value': {'doubleValue': classification.get('confidence', 0.0)}},
                    {'name': 'method', 'value': {'stringValue': classification.get('method', 'unknown')}},
                    {'name': 'metadata', 'value': {'stringValue': json.dumps(classification)}},
                    {'name': 'created_at', 'value': {'stringValue': datetime.utcnow().isoformat()}},
                    {'name': 'correlation_id', 'value': {'stringValue': self.correlation_id}}
                ]
            )
            
            logger.info(f"Stored classification results for news {news_id}")
            
        except Exception as e:
            logger.error(f"Error storing classification results: {str(e)}")
            raise
    
    def _update_news_classification(self, news_id: str, classification: Dict[str, Any]):
        """Update news item with classification results"""
        try:
            category_id = classification.get('category_id')
            confidence = classification.get('confidence', 0.0)
            
            rds.execute_statement(
                secretArn=DATABASE_SECRET_ARN,
                resourceArn=DATABASE_CLUSTER_ARN,
                database='jota_news',
                sql="""
                    UPDATE news_news 
                    SET category_id = :category_id, 
                        classification_confidence = :confidence,
                        is_processed = true,
                        updated_at = :updated_at
                    WHERE id = :news_id
                """,
                parameters=[
                    {'name': 'category_id', 'value': {'stringValue': category_id} if category_id else {'isNull': True}},
                    {'name': 'confidence', 'value': {'doubleValue': confidence}},
                    {'name': 'updated_at', 'value': {'stringValue': datetime.utcnow().isoformat()}},
                    {'name': 'news_id', 'value': {'stringValue': news_id}}
                ]
            )
            
            logger.info(f"Updated news {news_id} with classification")
            
        except Exception as e:
            logger.error(f"Error updating news classification: {str(e)}")
            raise
    
    def _send_classification_notification(self, news_id: str, classification: Dict[str, Any]):
        """Send notification about successful classification"""
        try:
            message = {
                'type': 'news_classified',
                'news_id': news_id,
                'category_id': classification.get('category_id'),
                'confidence': classification.get('confidence'),
                'method': classification.get('method'),
                'correlation_id': self.correlation_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            sns.publish(
                TopicArn=NOTIFICATION_TOPIC_ARN,
                Message=json.dumps(message),
                Subject=f"News Classified: {classification.get('category_name', 'Unknown')}",
                MessageAttributes={
                    'type': {
                        'StringValue': 'news_classified',
                        'DataType': 'String'
                    },
                    'correlation_id': {
                        'StringValue': self.correlation_id,
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Sent classification notification for news {news_id}")
            
        except Exception as e:
            logger.error(f"Error sending classification notification: {str(e)}")
            raise

def lambda_handler(event, context):
    """Main Lambda handler for news classification"""
    try:
        classifier = NewsClassifier()
        
        # Handle SQS event (batch processing)
        if 'Records' in event:
            results = []
            for record in event['Records']:
                if record.get('eventSource') == 'aws:sqs':
                    # Process SQS message
                    message_body = json.loads(record['body'])
                    result = classifier.classify_news(message_body)
                    results.append(result)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Batch classification completed',
                    'results': results
                })
            }
        
        # Handle direct invocation
        elif 'news_data' in event:
            result = classifier.classify_news(event['news_data'])
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
                'correlation_id': getattr(classifier, 'correlation_id', 'unknown')
            })
        }