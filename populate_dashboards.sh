#!/bin/bash
#
# Dashboard Population Script
# Generates activity to populate Grafana dashboards with real data
#

set -e

echo "🗞️  JOTA News System - Dashboard Population"
echo "============================================="

# Check if docker-compose is running
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Error: Docker Compose services are not running"
    echo "   Please start the system first: docker-compose up -d"
    exit 1
fi

echo "✅ Docker services are running"

# Wait for API to be ready
echo "⏳ Waiting for API to be ready..."
timeout=30
while [ $timeout -gt 0 ]; do
    if curl -s http://localhost:8000/health/ > /dev/null 2>&1; then
        echo "✅ API is ready"
        break
    fi
    sleep 2
    timeout=$((timeout-2))
done

if [ $timeout -le 0 ]; then
    echo "❌ API did not become ready in time"
    exit 1
fi

echo ""
echo "📊 Populating Dashboard Metrics..."
echo ""

# 1. Generate classification tasks
echo "1️⃣  Triggering Classification Tasks..."
docker-compose exec -T api python manage.py shell -c "
from apps.news.models import News
from apps.classification.tasks import classify_news

news_list = News.objects.all()[:10]
task_count = 0
for news in news_list:
    try:
        result = classify_news.delay(news.id)
        task_count += 1
        print(f'   ✓ Classification task {task_count}: {news.title[:40]}...')
    except Exception as e:
        print(f'   ⚠ Error: {e}')

print(f'   📈 Total classification tasks queued: {task_count}')
"

# 2. Generate webhook events
echo ""
echo "2️⃣  Generating Webhook Events..."
for i in {1..5}; do
    response=$(curl -s -X POST http://localhost:8000/api/v1/webhooks/receive/demo-source/ \
        -H "Content-Type: application/json" \
        -d "{
            \"title\": \"Dashboard Test News Article #$i\",
            \"content\": \"This test article will generate webhook and classification metrics for dashboard population.\",
            \"source\": \"Dashboard Populator\",
            \"author\": \"Test System\",
            \"category_hint\": \"technology\"
        }")
    
    if echo "$response" | grep -q "success\|queued"; then
        echo "   ✓ Webhook event $i processed"
    else
        echo "   ⚠ Webhook event $i failed"
    fi
    sleep 1
done

# 3. Wait for processing
echo ""
echo "3️⃣  Waiting for task processing..."
sleep 10

# 4. Check metrics
echo ""
echo "4️⃣  Verifying Metrics Collection..."

# Check Celery metrics
celery_metrics=$(curl -s http://localhost:8000/celery/metrics/ | grep "celery_tasks_total" | head -3)
if [ -n "$celery_metrics" ]; then
    echo "   ✅ Celery task metrics:"
    echo "$celery_metrics" | sed 's/^/      /'
else
    echo "   ⚠ No Celery metrics found"
fi

# Check business metrics
news_count=$(curl -s http://localhost:8000/business/metrics/ | grep "jota_news_articles_total" | head -1)
if [ -n "$news_count" ]; then
    echo "   ✅ News article metrics:"
    echo "$news_count" | sed 's/^/      /'
else
    echo "   ⚠ No news article metrics found (checking business metrics endpoint)"
fi

# Check webhook metrics
webhook_metrics=$(curl -s http://localhost:8000/business/metrics/ | grep "jota_webhooks_events_total" | head -2)
if [ -n "$webhook_metrics" ]; then
    echo "   ✅ Webhook metrics:"
    echo "$webhook_metrics" | sed 's/^/      /'
else
    echo "   ⚠ No webhook metrics found (they may take a moment to appear)"
fi

echo ""
echo "🎯 Dashboard Population Complete!"
echo ""
echo "📈 Access Your Dashboards:"
echo "   • Complete Dashboard:     http://localhost:3000/d/jota-news-complete"
echo "   • Celery Monitoring:      http://localhost:3000/d/celery-dashboard"
echo "   • Business Metrics:       http://localhost:3000/d/business-dashboard"
echo "   • Security Monitoring:    http://localhost:3000/d/security-dashboard"
echo "   • Redis Performance:      http://localhost:3000/d/redis-dashboard"
echo ""
echo "🔐 Grafana Login: admin / admin"
echo ""
echo "💡 To generate more activity, run this script again or use:"
echo "   python3 test_runner.py --demo"