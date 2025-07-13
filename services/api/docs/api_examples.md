# 📚 JOTA News System API Examples

This document provides comprehensive examples for using the JOTA News System API.

## 🔐 Authentication

### Obtain JWT Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

## 📰 News Management

### Create News Article

```bash
curl -X POST http://localhost:8000/api/v1/news/articles/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Breaking: New Technology Announced",
    "content": "Detailed article content about the new technology innovation...",
    "source": "Tech News Portal",
    "author": "John Doe",
    "category": "11111111-1111-1111-1111-111111111111",
    "tags": ["technology", "innovation"],
    "is_urgent": false,
    "metadata": {
      "original_url": "https://technews.com/article/123",
      "language": "pt-BR"
    }
  }'
```

### List News Articles

```bash
# Basic listing
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/news/articles/"

# With filters
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/news/articles/?category=poder&is_urgent=true&page=1"

# Search by text
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/news/articles/?search=reforma%20tributária"
```

### Get News Article Details

```bash
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/news/articles/12345678-1234-5678-9012-123456789012/"
```

### Update News Article

```bash
curl -X PATCH http://localhost:8000/api/v1/news/articles/12345678-1234-5678-9012-123456789012/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "is_urgent": true,
    "tags": ["technology", "innovation", "urgent"]
  }'
```

## 🏷️ Categories and Tags

### List Categories

```bash
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/news/categories/"
```

### Create Category

```bash
curl -X POST http://localhost:8000/api/v1/news/categories/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Economia",
    "description": "Notícias sobre economia e finanças",
    "keywords": ["economia", "finanças", "mercado", "investimentos"]
  }'
```

### List Tags

```bash
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/news/tags/"
```

## 🔗 Webhook Integration

### Create Webhook Source

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/sources/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "external-news-api",
    "description": "External news API webhook",
    "endpoint_url": "https://external-api.com/webhook",
    "secret_key": "your_secret_key_here",
    "expected_content_type": "application/json",
    "requires_authentication": true,
    "rate_limit_per_minute": 100
  }'
```

### Send News via Webhook

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/receive/external-news-api/ \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=calculated_hmac_signature" \
  -d '{
    "title": "News from External Source",
    "content": "Article content from external system...",
    "source": "External News API",
    "author": "External Author",
    "category_hint": "poder",
    "tags": ["governo", "política"],
    "is_urgent": false,
    "published_at": "2024-01-15T10:30:00Z",
    "metadata": {
      "original_id": "ext_123",
      "language": "pt-BR"
    }
  }'
```

### View Webhook Logs

```bash
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/webhooks/logs/?source=external-news-api&status=success"
```

## 🤖 Classification

### Classify News Text

```bash
curl -X POST http://localhost:8000/api/v1/classification/api/classify/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Governo anuncia nova reforma tributária",
    "content": "O governo federal anunciou hoje uma nova proposta de reforma do sistema tributário brasileiro...",
    "method": "hybrid"
  }'
```

**Response:**
```json
{
  "category": {
    "id": "22222222-2222-2222-2222-222222222222",
    "name": "Tributos",
    "confidence": 0.85
  },
  "subcategory": {
    "id": "aaaa1111-aaaa-1111-aaaa-111111111111",
    "name": "Reforma Tributária",
    "confidence": 0.92
  },
  "is_urgent": false,
  "urgency_confidence": 0.15,
  "keywords_found": ["governo", "reforma tributária", "tributário"],
  "method_used": "hybrid"
}
```

### List Classification Rules

```bash
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/classification/rules/"
```

## 📱 Notifications

### Create Notification Subscription

```bash
curl -X POST http://localhost:8000/api/v1/notifications/subscriptions/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "channel1-1111-1111-1111-111111111111",
    "destination": "+5511999999999",
    "min_priority": "medium",
    "categories": ["11111111-1111-1111-1111-111111111111"],
    "keywords": ["governo", "reforma"],
    "is_active": true,
    "notify_urgent_only": false
  }'
```

### Send Manual Notification

```bash
curl -X POST http://localhost:8000/api/v1/notifications/api/send/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "channel1-1111-1111-1111-111111111111",
    "destination": "+5511999999999",
    "subject": "🚨 URGENTE - JOTA",
    "message": "Nova notícia urgente sobre reforma tributária foi publicada.",
    "priority": "high",
    "template": "template1-1111-1111-1111-111111111111",
    "metadata": {
      "news_id": "12345678-1234-5678-9012-123456789012",
      "category": "tributos"
    }
  }'
```

### List Notification Channels

```bash
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/notifications/channels/"
```

## 📊 Monitoring and Statistics

### API Health Check

```bash
curl "http://localhost:8000/health/"
```

### API Statistics

```bash
curl "http://localhost:8000/health/stats/"
```

### Webhook Dashboard

```bash
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/webhooks/dashboard/"
```

## 🔍 Advanced Search

### Full-Text Search

```bash
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/news/articles/search/" \
  -d '{
    "query": "reforma tributária",
    "category": "tributos",
    "date_from": "2024-01-01",
    "date_to": "2024-01-31"
  }'
```

### Search with Filters

```bash
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/news/articles/?search=governo&category=poder&is_urgent=true&ordering=-created_at"
```

## 💡 Best Practices

### 1. Error Handling

Always check response status codes and handle errors gracefully:

```bash
response=$(curl -s -w "%{http_code}" -o /tmp/response.json \
  -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/news/articles/")

http_code=${response: -3}
if [ "$http_code" -eq 200 ]; then
  echo "Success"
  cat /tmp/response.json
else
  echo "Error: HTTP $http_code"
  cat /tmp/response.json
fi
```

### 2. Pagination

Handle paginated responses properly:

```bash
curl -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/news/articles/?page=1&page_size=20"
```

### 3. Rate Limiting

Respect rate limits and implement backoff strategies:

```bash
# Check rate limit headers in response
curl -I -H "Authorization: Bearer <your_access_token>" \
  "http://localhost:8000/api/v1/news/articles/"
```

### 4. Webhook Signature Verification

When implementing webhook receivers, always verify signatures:

```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected_signature}", signature)
```

## 🔧 Development Tools

### Generate Test Token

```bash
# Using Django shell
docker-compose exec api python manage.py shell -c "
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
user = User.objects.get(username='admin')
token = RefreshToken.for_user(user)
print(f'Access Token: {token.access_token}')
print(f'Refresh Token: {token}')
"
```

### Create Test Data

```bash
# Load sample data
docker-compose exec api python manage.py loaddata fixtures/sample_data.json
```

### Monitor Logs

```bash
# Follow API logs
docker-compose logs -f api

# Follow webhook processing
docker-compose logs -f celery_worker
```

## 🚀 Production Considerations

### 1. Security Headers

Always include proper security headers:

```bash
curl -H "Authorization: Bearer <your_access_token>" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "X-Forwarded-Proto: https" \
  "https://api.jota.news/api/v1/news/articles/"
```

### 2. HTTPS Only

Never send credentials over HTTP:

```bash
# ❌ Never do this in production
curl -H "Authorization: Bearer <token>" "http://api.jota.news/..."

# ✅ Always use HTTPS
curl -H "Authorization: Bearer <token>" "https://api.jota.news/..."
```

### 3. Token Management

Implement proper token rotation:

```bash
# Refresh tokens before they expire
curl -X POST https://api.jota.news/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```