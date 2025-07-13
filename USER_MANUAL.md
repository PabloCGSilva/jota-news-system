# JOTA News System - User Manual

## Table of Contents

1. [Getting Started](#getting-started)
2. [User Interface Guide](#user-interface-guide)
3. [API Usage Guide](#api-usage-guide)
4. [Authentication](#authentication)
5. [Managing News Articles](#managing-news-articles)
6. [Categories and Tags](#categories-and-tags)
7. [Webhook Integration](#webhook-integration)
8. [Notifications Setup](#notifications-setup)
9. [Monitoring and Analytics](#monitoring-and-analytics)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Features](#advanced-features)

---

## Getting Started

### System Requirements

The JOTA News System runs completely out-of-the-box with no external dependencies:
- **Web Browser**: Modern browser (Chrome, Firefox, Safari, Edge)
- **Local Access**: System is self-contained and accessible locally
- **Demo Mode**: Complete functionality available immediately after setup

### Accessing the System

#### Web Interface
1. **Main Dashboard**: Navigate to `http://localhost:8000/` (or your deployment URL)
2. **Demo Interface**: Visit `http://localhost:8000/demo/` for testing features
3. **API Documentation**: Browse to `http://localhost:8000/api/docs/` for interactive API docs
4. **Admin Panel**: Access `http://localhost:8000/admin/` (default: admin/admin123)

**Note**: The system includes pre-configured demo data including admin user, categories, sample articles, and notification channels for immediate testing.

#### Monitoring Dashboards
- **Grafana**: `http://localhost:3000/` (admin/admin)
- **RabbitMQ Management**: `http://localhost:15672/` (guest/guest)
- **Redis Commander**: `http://localhost:8081/` (admin/admin)

---

## User Interface Guide

### Main Dashboard

The main dashboard provides an overview of your news system:

#### Key Features:
- **Real-time Statistics**: Total articles, urgent news, categories, and notifications
- **Recent News Feed**: Latest articles with urgency indicators
- **System Status**: Health monitoring for all services
- **Quick Actions**: Create test content and run system checks

#### Navigation:
- **Header Menu**: Access admin panel and API documentation
- **Refresh Button**: Update dashboard data manually
- **Auto-refresh**: Dashboard updates every 30 seconds automatically

### Demo Interface

The demo interface allows you to test system functionality:

#### Available Actions:

1. **Create Sample News**
   - Generates 3 sample articles across different categories
   - Articles include AI classification confidence scores
   - Urgent news items are flagged automatically

2. **Test Classification**
   - Runs AI classification on existing articles
   - Shows confidence scores and processing time
   - Demonstrates hybrid keyword + ML approach

3. **Test Webhook Processing**
   - Simulates external news feed integration
   - Custom data input via modal dialog
   - Creates webhook logs for monitoring

4. **Generate Load**
   - Creates 10 test articles for performance testing
   - Generates webhook logs for analytics
   - Useful for monitoring system under load

5. **Health Checks**
   - Tests all system components
   - Verifies database connectivity
   - Checks API endpoint availability

#### System Testing Features:
- **Activity Log**: Real-time log of all actions performed
- **Notification Toast**: Success/error feedback for operations
- **Loading Indicators**: Visual feedback during processing

---

## API Usage Guide

### Base URLs

- **Development**: `http://localhost:8000/api/v1/`
- **Production**: `https://your-domain.com/api/v1/`

### Response Format

All API responses follow this structure:
```json
{
  "count": 123,
  "next": "http://example.com/api/v1/news/articles/?page=2",
  "previous": null,
  "results": [
    // Array of objects
  ]
}
```

### Status Codes

- **200 OK**: Successful request
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

---

## Authentication

### Method 1: JWT Tokens (Recommended for Web Applications)

#### Step 1: Obtain Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Step 2: Use Access Token
```bash
curl -X GET http://localhost:8000/api/v1/news/articles/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

#### Step 3: Refresh Token (when access token expires)
```bash
curl -X POST http://localhost:8000/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

### Method 2: API Keys (Recommended for Third-party Integrations)

#### Step 1: Create API Key
```bash
curl -X POST http://localhost:8000/api/v1/auth/api-keys/ \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Integration",
    "description": "API key for external system integration"
  }'
```

#### Step 2: Use API Key
```bash
curl -X GET http://localhost:8000/api/v1/news/articles/ \
  -H "X-API-Key: your_api_key_here"
```

### Method 3: Session Authentication (For Web Interface)

Automatically handled by the Django web interface when logged in through the admin panel.

---

## Managing News Articles

### Viewing News Articles

#### Get All Articles
```bash
curl -X GET "http://localhost:8000/api/v1/news/articles/" \
  -H "Authorization: Bearer your_token"
```

#### Filter by Category
```bash
curl -X GET "http://localhost:8000/api/v1/news/articles/?category=technology" \
  -H "Authorization: Bearer your_token"
```

#### Search Articles
```bash
curl -X GET "http://localhost:8000/api/v1/news/articles/?search=artificial%20intelligence" \
  -H "Authorization: Bearer your_token"
```

#### Filter by Date
```bash
curl -X GET "http://localhost:8000/api/v1/news/articles/?published_after=2024-01-01" \
  -H "Authorization: Bearer your_token"
```

#### Get Urgent News Only
```bash
curl -X GET "http://localhost:8000/api/v1/news/articles/?is_urgent=true" \
  -H "Authorization: Bearer your_token"
```

### Creating News Articles

#### Basic Article Creation
```bash
curl -X POST http://localhost:8000/api/v1/news/articles/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Breaking: New Technology Breakthrough",
    "content": "Scientists have made a significant breakthrough in quantum computing...",
    "summary": "Quantum computing breakthrough achieves new milestone.",
    "source": "Tech News Today",
    "author": "Dr. Jane Smith",
    "external_id": "tech-news-2024-001",
    "category_id": "uuid-of-technology-category",
    "is_urgent": true,
    "tags": ["technology", "quantum", "breakthrough"]
  }'
```

#### Automatic Classification
The system automatically classifies articles using AI when created. The classification includes:
- **Category Assignment**: Based on content analysis
- **Confidence Score**: How certain the AI is about the classification
- **Urgency Detection**: Whether the article should be marked as urgent

### Updating Articles

#### Update Specific Fields
```bash
curl -X PATCH http://localhost:8000/api/v1/news/articles/article-uuid/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "is_urgent": false,
    "summary": "Updated summary text"
  }'
```

#### Mark Article as Urgent
```bash
curl -X POST http://localhost:8000/api/v1/news/articles/article-uuid/mark_urgent/ \
  -H "Authorization: Bearer your_token"
```

### Article Statistics

#### View Article Statistics
```bash
curl -X GET http://localhost:8000/api/v1/news/articles/article-uuid/statistics/ \
  -H "Authorization: Bearer your_token"
```

**Response includes:**
- View count
- Share count
- Classification confidence
- Processing time
- Related articles

---

## Categories and Tags

### Managing Categories

#### List All Categories
```bash
curl -X GET http://localhost:8000/api/v1/news/categories/ \
  -H "Authorization: Bearer your_token"
```

#### Create New Category
```bash
curl -X POST http://localhost:8000/api/v1/news/categories/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Artificial Intelligence",
    "description": "News about AI and machine learning",
    "keywords": ["AI", "machine learning", "neural networks", "deep learning"],
    "is_active": true
  }'
```

#### Category Statistics
```bash
curl -X GET http://localhost:8000/api/v1/news/categories/category-uuid/statistics/ \
  -H "Authorization: Bearer your_token"
```

### Managing Tags

#### List All Tags
```bash
curl -X GET http://localhost:8000/api/v1/news/tags/ \
  -H "Authorization: Bearer your_token"
```

#### Create New Tag
```bash
curl -X POST http://localhost:8000/api/v1/news/tags/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "breakthrough",
    "description": "Scientific or technological breakthroughs"
  }'
```

---

## Webhook Integration

### Setting Up Webhook Sources

#### Create Webhook Source
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/sources/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "External News Feed",
    "description": "Primary news feed from external provider",
    "endpoint_url": "https://your-domain.com/api/v1/webhooks/receive/external-feed/",
    "secret_key": "your-secret-key-for-signature-verification",
    "is_active": true,
    "requires_authentication": true,
    "rate_limit_per_minute": 60,
    "retry_count": 3,
    "retry_delay_seconds": 30
  }'
```

### Sending News via Webhook

#### Webhook Endpoint Format
**URL**: `POST /api/v1/webhooks/receive/{source_name}/`

#### Required Headers
```
Content-Type: application/json
X-Signature-256: sha256=computed_signature
```

#### Signature Calculation
```python
import hmac
import hashlib

secret_key = "your-webhook-secret-key"
payload = json.dumps(your_data)
signature = hmac.new(
    secret_key.encode(),
    payload.encode(),
    hashlib.sha256
).hexdigest()
```

#### Webhook Payload Example
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/receive/external-feed/ \
  -H "Content-Type: application/json" \
  -H "X-Signature-256: sha256=computed_signature" \
  -d '{
    "title": "Webhook News Article",
    "content": "This article was created via webhook integration...",
    "source": "External News Provider",
    "author": "External Author",
    "published_at": "2024-01-15T10:30:00Z",
    "external_id": "ext-news-12345",
    "tags": ["webhook", "integration"],
    "metadata": {
      "priority": "high",
      "region": "global"
    }
  }'
```

### Monitoring Webhook Activity

#### View Webhook Logs
```bash
curl -X GET http://localhost:8000/api/v1/webhooks/logs/ \
  -H "Authorization: Bearer your_token"
```

#### Filter by Source
```bash
curl -X GET "http://localhost:8000/api/v1/webhooks/logs/?source=external-feed" \
  -H "Authorization: Bearer your_token"
```

#### Filter by Status
```bash
curl -X GET "http://localhost:8000/api/v1/webhooks/logs/?status=failed" \
  -H "Authorization: Bearer your_token"
```

---

## Notifications Setup

### Creating Notification Channels

The system comes with pre-configured demo notification channels for immediate testing.

#### Email Channel (Console Backend)
```bash
curl -X POST http://localhost:8000/api/v1/notifications/channels/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Console Email Notifications",
    "channel_type": "email",
    "is_active": true,
    "config": {},
    "rate_limit_per_minute": 10
  }'
```

#### Slack Channel (Demo Mode)
```bash
curl -X POST http://localhost:8000/api/v1/notifications/channels/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo Slack Alerts",
    "channel_type": "slack",
    "is_active": true,
    "config": {
      "webhook_url": "http://localhost:8000/demo/slack",
      "channel": "#news-alerts",
      "username": "JOTA News Bot"
    },
    "rate_limit_per_minute": 30
  }'
```

#### Webhook Channel (Demo Mode)
```bash
curl -X POST http://localhost:8000/api/v1/notifications/channels/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo Webhook Channel",
    "channel_type": "webhook",
    "is_active": true,
    "config": {
      "url": "http://localhost:8000/demo/webhook",
      "method": "POST",
      "headers": {
        "Authorization": "Bearer external-system-token"
      }
    },
    "rate_limit_per_minute": 100
  }'
```

### Creating Notification Subscriptions

#### Subscribe to Urgent News
```bash
curl -X POST http://localhost:8000/api/v1/notifications/subscriptions/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Urgent News Alerts",
    "channel_id": "uuid-of-notification-channel",
    "is_active": true,
    "filters": {
      "is_urgent": true,
      "categories": ["technology", "politics"],
      "keywords": ["breaking", "urgent", "alert"]
    },
    "schedule": {
      "immediate": true,
      "quiet_hours": {
        "start": "22:00",
        "end": "08:00",
        "timezone": "America/Sao_Paulo"
      }
    },
    "template_config": {
      "include_summary": true,
      "include_link": true,
      "max_length": 500
    }
  }'
```

#### Daily Summary Subscription
```bash
curl -X POST http://localhost:8000/api/v1/notifications/subscriptions/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily News Summary",
    "channel_id": "uuid-of-email-channel",
    "is_active": true,
    "schedule": {
      "type": "daily",
      "time": "08:00",
      "timezone": "America/Sao_Paulo",
      "days_of_week": ["monday", "tuesday", "wednesday", "thursday", "friday"]
    },
    "filters": {
      "categories": ["business", "technology"],
      "exclude_urgent": false
    },
    "template_config": {
      "format": "summary",
      "max_articles": 10,
      "include_images": true
    }
  }'
```

### Notification Templates

#### Custom Email Template
```bash
curl -X POST http://localhost:8000/api/v1/notifications/templates/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Urgent News Email",
    "channel_type": "email",
    "subject_template": "🚨 URGENT: {{title}}",
    "body_template": "
      <h2>{{title}}</h2>
      <p><strong>Source:</strong> {{source}}</p>
      <p><strong>Author:</strong> {{author}}</p>
      <p><strong>Published:</strong> {{published_at}}</p>
      
      <div>{{content}}</div>
      
      <p><a href=\"{{link}}\">Read Full Article</a></p>
      
      <hr>
      <small>This is an automated notification from JOTA News System</small>
    ",
    "is_active": true
  }'
```

---

## Monitoring and Analytics

### Accessing Monitoring Dashboards

#### Grafana Dashboards

1. **Main Dashboard**: Overview of system health and performance
   - URL: `http://localhost:3000/d/jota-news-complete/`
   - Metrics: API requests, response times, error rates

2. **Business Dashboard**: Business-specific KPIs
   - URL: `http://localhost:3000/d/business-dashboard/`
   - Metrics: News processed, classification accuracy, user engagement

3. **Celery Dashboard**: Background task monitoring
   - URL: `http://localhost:3000/d/celery-dashboard/`
   - Metrics: Task processing times, queue depths, worker health

4. **Security Dashboard**: Security monitoring
   - URL: `http://localhost:3000/d/security-dashboard/`
   - Metrics: Failed logins, API rate limiting, suspicious activity

#### Key Metrics to Monitor

1. **System Performance**
   - API response times (< 2 seconds target)
   - Database query performance
   - Memory and CPU usage
   - Queue processing times

2. **Business Metrics**
   - News articles processed per hour
   - Classification accuracy percentage
   - Notification delivery rates
   - User engagement metrics

3. **Error Monitoring**
   - API error rates (< 1% target)
   - Failed webhook deliveries
   - Classification failures
   - Notification delivery failures

### Health Check Endpoints

#### System Health
```bash
curl -X GET http://localhost:8000/health/
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "celery": "healthy"
  },
  "version": "1.0.0"
}
```

#### Detailed Health Checks
```bash
# Celery workers
curl -X GET http://localhost:8000/celery/health/

# Business metrics
curl -X GET http://localhost:8000/business/health/

# Security status
curl -X GET http://localhost:8000/security/health/
```

### Prometheus Metrics

#### Available Metrics Endpoints
- **Django Metrics**: `http://localhost:8000/metrics/`
- **Business Metrics**: `http://localhost:8000/business/metrics/`
- **Celery Metrics**: `http://localhost:8000/celery/metrics/`
- **Security Metrics**: `http://localhost:8000/security/metrics/`

#### Key Metrics

1. **News Processing Metrics**
   ```
   jota_news_articles_total{category="technology",status="published"}
   jota_news_processing_time_seconds_bucket
   jota_classification_accuracy{model_type="hybrid"}
   ```

2. **API Metrics**
   ```
   django_http_requests_total{method="GET",status="200"}
   django_http_request_duration_seconds
   django_http_responses_total
   ```

3. **Notification Metrics**
   ```
   jota_notification_delivery_total{channel="email",status="success"}
   jota_notification_delivery_time_seconds
   ```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Authentication Errors

**Problem**: `401 Unauthorized` responses
**Solutions**:
- Verify JWT token hasn't expired (60-minute lifetime)
- Check token format: `Authorization: Bearer <token>`
- Refresh token if necessary
- Ensure API key is included: `X-API-Key: <key>`

**Debug Steps**:
```bash
# Verify token
curl -X POST http://localhost:8000/api/v1/auth/token/verify/ \
  -H "Content-Type: application/json" \
  -d '{"token": "your_access_token"}'

# Get new token
curl -X POST http://localhost:8000/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "your_refresh_token"}'
```

#### 2. Webhook Processing Failures

**Problem**: Webhooks returning 400 or 500 errors
**Solutions**:
- Verify signature calculation
- Check JSON payload format
- Ensure webhook source exists and is active
- Verify rate limits aren't exceeded

**Debug Steps**:
```bash
# Check webhook logs
curl -X GET "http://localhost:8000/api/v1/webhooks/logs/?status=failed" \
  -H "Authorization: Bearer your_token"

# Verify webhook source
curl -X GET http://localhost:8000/api/v1/webhooks/sources/ \
  -H "Authorization: Bearer your_token"
```

#### 3. Classification Not Working

**Problem**: Articles not being classified automatically
**Solutions**:
- Check if Celery workers are running
- Verify classification models are loaded
- Check for sufficient training data

**Debug Steps**:
```bash
# Check Celery status
curl -X GET http://localhost:8000/celery/health/

# Manual classification
curl -X POST http://localhost:8000/api/v1/classification/classify/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"article_id": "uuid-of-article"}'
```

#### 4. Notification Delivery Issues

**Problem**: Notifications not being sent
**Solutions**:
- Verify notification channels are active
- Check subscription filters and schedules
- Note: System uses console email backend and demo modes for notifications
- Verify rate limits

**Debug Steps**:
```bash
# Check notification status
curl -X GET http://localhost:8000/api/v1/notifications/channels/ \
  -H "Authorization: Bearer your_token"

# Test notification
curl -X POST http://localhost:8000/api/v1/notifications/test/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"channel_id": "uuid", "message": "Test notification"}'
```

#### 5. Performance Issues

**Problem**: Slow API responses or timeouts
**Solutions**:
- Check database query performance
- Verify Redis cache is working
- Monitor Celery queue depths
- Check system resources (CPU, memory)

**Debug Steps**:
```bash
# Check system health
curl -X GET http://localhost:8000/health/

# Check metrics
curl -X GET http://localhost:8000/metrics/

# Monitor in Grafana
# Visit: http://localhost:3000/d/jota-news-complete/
```

### Error Response Format

All API errors follow this format:
```json
{
  "error": "Brief error description",
  "detail": "Detailed error information",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "uuid-for-tracing"
}
```

### Log Analysis

#### Application Logs Location
- **Django**: `/services/api/logs/django.log`
- **Celery**: Check Docker logs: `docker-compose logs worker`
- **Nginx**: Check Docker logs: `docker-compose logs nginx`

#### Log Levels
- **ERROR**: Critical issues requiring immediate attention
- **WARNING**: Issues that might affect functionality
- **INFO**: General information about operations
- **DEBUG**: Detailed debugging information

---

## Advanced Features

### Custom Classification Rules

#### Create Keyword-based Rule
```bash
curl -X POST http://localhost:8000/api/v1/classification/rules/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI Technology Rule",
    "rule_type": "keyword",
    "target_category_id": "uuid-of-ai-category",
    "keywords": ["artificial intelligence", "machine learning", "neural network"],
    "confidence_threshold": 0.8,
    "priority": 1,
    "is_active": true
  }'
```

#### Create Pattern-based Rule
```bash
curl -X POST http://localhost:8000/api/v1/classification/rules/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Financial News Pattern",
    "rule_type": "pattern",
    "target_category_id": "uuid-of-finance-category",
    "pattern": "\\b(stock|market|trading|investment|financial)\\b.*\\b(rises?|falls?|gains?|losses?)\\b",
    "confidence_threshold": 0.75,
    "priority": 2,
    "is_active": true
  }'
```

### Bulk Operations

#### Bulk Article Creation
```bash
curl -X POST http://localhost:8000/api/v1/news/articles/bulk_create/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "articles": [
      {
        "title": "Article 1",
        "content": "Content 1",
        "source": "Source 1",
        "external_id": "bulk-1"
      },
      {
        "title": "Article 2", 
        "content": "Content 2",
        "source": "Source 2",
        "external_id": "bulk-2"
      }
    ]
  }'
```

#### Bulk Classification
```bash
curl -X POST http://localhost:8000/api/v1/classification/bulk_classify/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "article_ids": ["uuid1", "uuid2", "uuid3"],
    "method": "hybrid",
    "force_reclassify": false
  }'
```

### Advanced Search

#### Complex Search Query
```bash
curl -X GET "http://localhost:8000/api/v1/news/articles/search/" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence",
    "filters": {
      "categories": ["technology", "science"],
      "date_range": {
        "start": "2024-01-01",
        "end": "2024-01-31"
      },
      "sources": ["Tech Daily", "AI News"],
      "is_urgent": false,
      "min_confidence": 0.8
    },
    "sort": [
      {"field": "published_at", "order": "desc"},
      {"field": "category_confidence", "order": "desc"}
    ],
    "limit": 20,
    "offset": 0
  }'
```

#### Full-text Search with Highlighting
```bash
curl -X GET "http://localhost:8000/api/v1/news/articles/?search=quantum%20computing&highlight=true" \
  -H "Authorization: Bearer your_token"
```

### Export and Reporting

#### Export Articles to CSV
```bash
curl -X GET "http://localhost:8000/api/v1/news/articles/export/?format=csv&category=technology" \
  -H "Authorization: Bearer your_token" \
  -o "news_articles.csv"
```

#### Export Articles to JSON
```bash
curl -X GET "http://localhost:8000/api/v1/news/articles/export/?format=json&date_from=2024-01-01" \
  -H "Authorization: Bearer your_token" \
  -o "news_articles.json"
```

#### Generate Analytics Report
```bash
curl -X POST http://localhost:8000/api/v1/news/reports/analytics/ \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-01-31"
    },
    "grouping": "category",
    "metrics": ["count", "avg_confidence", "urgent_ratio"],
    "format": "json"
  }'
```

### WebSocket Real-time Updates

#### Connect to Real-time Feed
```javascript
// WebSocket connection for real-time news updates
const ws = new WebSocket('ws://localhost:8000/ws/news/');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('New news update:', data);
    
    switch(data.type) {
        case 'new_article':
            // Handle new article
            break;
        case 'urgent_news':
            // Handle urgent news alert
            break;
        case 'classification_update':
            // Handle classification result
            break;
    }
};

// Subscribe to specific channels
ws.send(JSON.stringify({
    'action': 'subscribe',
    'channels': ['urgent_news', 'technology', 'politics']
}));
```

---

## Conclusion

This user manual provides comprehensive guidance for using the JOTA News System effectively. The system offers powerful features for news management, AI-powered classification, webhook integration, and real-time notifications.

### Key Takeaways:

1. **Multiple Access Methods**: Web interface, REST API, and demo environment
2. **Flexible Authentication**: JWT tokens for web apps, API keys for integrations
3. **Automated Processing**: AI classification and intelligent routing
4. **Real-time Capabilities**: WebSocket updates and instant notifications
5. **Comprehensive Monitoring**: Built-in analytics and health monitoring
6. **Scalable Architecture**: Designed for high-volume news processing

### Next Steps:

1. **Start with Demo**: Use the demo interface to understand system capabilities
2. **Set Up Authentication**: Create API keys or JWT tokens for your use case
3. **Configure Notifications**: Set up channels and subscriptions for your needs
4. **Monitor Performance**: Use Grafana dashboards to track system health
5. **Scale Gradually**: Start with basic features and add advanced capabilities as needed

### Support and Resources:

- **API Documentation**: `http://localhost:8000/api/docs/`
- **Grafana Monitoring**: `http://localhost:3000/`
- **Demo Interface**: `http://localhost:8000/demo/`
- **Health Checks**: `http://localhost:8000/health/`

For additional support or feature requests, refer to the system administrator or development team.