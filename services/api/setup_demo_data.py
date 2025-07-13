#!/usr/bin/env python
"""
Demo data setup script for JOTA News System.
Creates default categories, notification channels, and sample data for immediate out-of-the-box functionality.
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jota_news.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.news.models import Category, Subcategory, Tag, News
from apps.notifications.models import NotificationChannel, NotificationSubscription
from apps.webhooks.models import WebhookSource
from apps.classification.models import ClassificationRule
from django.utils import timezone
import uuid

User = get_user_model()

def create_demo_data():
    """Create demo data for immediate functionality."""
    
    print("🚀 Setting up JOTA News System demo data...")
    
    # 1. Create superuser if it doesn't exist
    if not User.objects.filter(is_superuser=True).exists():
        user = User.objects.create_superuser(
            username='admin',
            email='admin@jota-news-demo.local',
            password='admin123',
            first_name='Demo',
            last_name='Admin'
        )
        print("✅ Created demo admin user (admin/admin123)")
    else:
        user = User.objects.filter(is_superuser=True).first()
        print("✅ Admin user already exists")
    
    # 2. Create main categories
    categories_data = [
        {'name': 'Poder', 'description': 'Notícias sobre governo, política e poder público', 
         'keywords': ['governo', 'política', 'congresso', 'executivo', 'legislativo', 'judiciário', 'eleições']},
        {'name': 'Tributos', 'description': 'Notícias sobre impostos e tributação', 
         'keywords': ['impostos', 'receita federal', 'tributação', 'reforma tributária', 'fisco']},
        {'name': 'Saúde', 'description': 'Notícias sobre saúde pública e medicina', 
         'keywords': ['saúde pública', 'medicina', 'hospitais', 'anvisa', 'sus']},
        {'name': 'Trabalhista', 'description': 'Notícias sobre trabalho e previdência', 
         'keywords': ['trabalho', 'previdência', 'emprego', 'sindicatos', 'clt']},
        {'name': 'Tecnologia', 'description': 'Notícias sobre tecnologia e inovação', 
         'keywords': ['tecnologia', 'inovação', 'digital', 'ia', 'inteligência artificial']},
    ]
    
    categories = {}
    for cat_data in categories_data:
        category, created = Category.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'description': cat_data['description'],
                'keywords': cat_data['keywords'],
                'is_active': True
            }
        )
        categories[cat_data['name']] = category
        if created:
            print(f"✅ Created category: {cat_data['name']}")
    
    # 3. Create subcategories
    subcategories_data = [
        {'name': 'Aposta da Semana', 'category': 'Tributos', 'description': 'Análises semanais tributárias'},
        {'name': 'Matinal', 'category': 'Poder', 'description': 'Notícias matinais de política'},
        {'name': 'Urgente', 'category': 'Poder', 'description': 'Notícias urgentes do poder público'},
        {'name': 'Reforma Tributária', 'category': 'Tributos', 'description': 'Notícias sobre reforma tributária'},
    ]
    
    for sub_data in subcategories_data:
        subcategory, created = Subcategory.objects.get_or_create(
            name=sub_data['name'],
            category=categories[sub_data['category']],
            defaults={'description': sub_data['description'], 'is_active': True}
        )
        if created:
            print(f"✅ Created subcategory: {sub_data['name']}")
    
    # 4. Create basic tags
    tags_data = [
        'Reforma Tributária', 'Imposto de Renda', 'Saúde Pública', 'Congresso Nacional',
        'STF', 'Governo Federal', 'Previdência Social', 'CLT', 'ANVISA', 'SUS',
        'Eleições', 'Política', 'Judiciário', 'Legislativo', 'Executivo'
    ]
    
    for tag_name in tags_data:
        tag, created = Tag.objects.get_or_create(name=tag_name)
        if created:
            print(f"✅ Created tag: {tag_name}")
    
    # 5. Create classification rules
    rules_data = [
        {'name': 'Poder Keywords', 'rule_type': 'keyword', 'category': 'Poder', 
         'keywords': ['governo', 'política', 'congresso', 'executivo', 'legislativo'], 'priority': 1},
        {'name': 'Tributos Keywords', 'rule_type': 'keyword', 'category': 'Tributos', 
         'keywords': ['impostos', 'receita federal', 'tributação', 'reforma tributária'], 'priority': 1},
        {'name': 'Saúde Keywords', 'rule_type': 'keyword', 'category': 'Saúde', 
         'keywords': ['saúde pública', 'medicina', 'hospitais', 'anvisa'], 'priority': 1},
        {'name': 'Trabalhista Keywords', 'rule_type': 'keyword', 'category': 'Trabalhista', 
         'keywords': ['trabalho', 'previdência', 'emprego', 'sindicatos'], 'priority': 1},
    ]
    
    for rule_data in rules_data:
        rule, created = ClassificationRule.objects.get_or_create(
            name=rule_data['name'],
            defaults={
                'rule_type': rule_data['rule_type'],
                'target_category': categories[rule_data['category']],
                'keywords': rule_data['keywords'],
                'confidence_threshold': 0.7,
                'priority': rule_data['priority'],
                'is_active': True
            }
        )
        if created:
            print(f"✅ Created classification rule: {rule_data['name']}")
    
    # 6. Create demo notification channels
    channels_data = [
        {'name': 'Console Email', 'channel_type': 'email', 'config': {}, 'is_active': True},
        {'name': 'Demo Webhook', 'channel_type': 'webhook', 'config': {'url': 'http://localhost:8000/demo/webhook'}, 'is_active': True},
        {'name': 'Demo Slack', 'channel_type': 'slack', 'config': {'webhook_url': 'http://localhost:8000/demo/slack'}, 'is_active': True},
        {'name': 'Mock SMS', 'channel_type': 'sms', 'config': {}, 'is_active': True},
    ]
    
    for channel_data in channels_data:
        channel, created = NotificationChannel.objects.get_or_create(
            name=channel_data['name'],
            defaults={
                'channel_type': channel_data['channel_type'],
                'config': channel_data['config'],
                'is_active': channel_data['is_active'],
                'rate_limit_per_minute': 60
            }
        )
        if created:
            print(f"✅ Created notification channel: {channel_data['name']}")
    
    # 7. Create demo webhook source
    webhook_source, created = WebhookSource.objects.get_or_create(
        name='demo-source',
        defaults={
            'description': 'Demo webhook source for testing',
            'endpoint_url': 'http://localhost:8000/api/v1/webhooks/receive/demo-source/',
            'secret_key': 'demo-secret-key-123',
            'is_active': True,
            'requires_authentication': False,
            'rate_limit_per_minute': 100
        }
    )
    if created:
        print("✅ Created demo webhook source")
    
    # 8. Create sample news articles
    sample_articles = [
        {
            'title': 'Congresso aprova nova reforma tributária',
            'content': 'O Congresso Nacional aprovou hoje uma importante reforma no sistema tributário brasileiro, que promete simplificar a cobrança de impostos e reduzir a carga tributária para pequenas empresas.',
            'source': 'JOTA Demo',
            'author': 'Redação JOTA',
            'category': categories['Tributos'],
            'is_urgent': False,
            'tags': ['Reforma Tributária', 'Congresso Nacional']
        },
        {
            'title': 'STF julga caso sobre saúde pública',
            'content': 'O Supremo Tribunal Federal iniciou hoje o julgamento de um importante caso sobre financiamento da saúde pública no Brasil, que pode ter impacto direto no orçamento do SUS.',
            'source': 'JOTA Demo',
            'author': 'Correspondente STF',
            'category': categories['Saúde'],
            'is_urgent': True,
            'tags': ['STF', 'Saúde Pública', 'SUS']
        },
        {
            'title': 'Nova regulamentação trabalhista entra em vigor',
            'content': 'Entra em vigor hoje a nova regulamentação trabalhista que altera aspectos importantes da CLT, especialmente no que se refere ao trabalho remoto e jornada flexível.',
            'source': 'JOTA Demo',
            'author': 'Editor Trabalhista',
            'category': categories['Trabalhista'],
            'is_urgent': False,
            'tags': ['CLT', 'Trabalho remoto']
        }
    ]
    
    for article_data in sample_articles:
        # Create unique external_id
        external_id = f"demo-{uuid.uuid4().hex[:8]}"
        
        article, created = News.objects.get_or_create(
            external_id=external_id,
            defaults={
                'title': article_data['title'],
                'content': article_data['content'],
                'source': article_data['source'],
                'author': article_data['author'],
                'category': article_data['category'],
                'is_urgent': article_data['is_urgent'],
                'is_published': True,
                'published_at': timezone.now()
            }
        )
        
        if created:
            # Add tags
            for tag_name in article_data['tags']:
                tag = Tag.objects.get(name=tag_name)
                article.tags.add(tag)
            article.save()
            print(f"✅ Created sample article: {article_data['title']}")
    
    print("\n🎉 Demo data setup complete!")
    print("\nYou can now:")
    print("1. Access the admin at http://localhost:8000/admin/ (admin/admin123)")
    print("2. View the demo dashboard at http://localhost:8000/demo/")
    print("3. Test the API at http://localhost:8000/api/docs/")
    print("4. Send test webhooks to http://localhost:8000/api/v1/webhooks/receive/demo-source/")
    print("\nThe system is ready for immediate use with no external dependencies! 🚀")

if __name__ == '__main__':
    create_demo_data()