#!/usr/bin/env python3
"""
Enhanced Demo Data Generator for JOTA News System
Creates realistic Brazilian news data with proper classification and user behavior patterns.
"""
import os
import sys
import django
import random
import requests
from datetime import datetime, timedelta
from faker import Faker

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jota_news.settings')
sys.path.append('/app')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.news.models import Category, News, Tag
from apps.authentication.models import APIKey, UserProfile
from apps.notifications.models import NotificationChannel, NotificationSubscription
from apps.webhooks.models import WebhookSource

User = get_user_model()
fake = Faker('pt_BR')

# Brazilian Political/Economic News Templates
NEWS_TEMPLATES = {
    'politica': [
        {
            'title': 'Congresso Nacional aprova nova lei de transparência pública',
            'content': 'O Congresso Nacional aprovou hoje, por ampla maioria, a nova lei de transparência pública que estabelece critérios mais rigorosos para divulgação de informações governamentais. A proposta, que tramitou por dois anos no Legislativo, recebeu apoio de parlamentares de diferentes partidos.',
            'summary': 'Nova lei de transparência é aprovada com amplo apoio parlamentar',
            'tags': ['transparencia', 'congresso', 'lei', 'governanca']
        },
        {
            'title': 'Supremo Tribunal Federal julga constitucionalidade de marco fiscal',
            'content': 'O Supremo Tribunal Federal iniciou hoje o julgamento sobre a constitucionalidade do novo marco fiscal brasileiro. Os ministros devem analisar questionamentos sobre limites de gastos públicos e sua compatibilidade com direitos sociais constitucionais.',
            'summary': 'STF analisa constitucionalidade do marco fiscal em sessão histórica',
            'tags': ['stf', 'fiscal', 'constituicao', 'orcamento']
        }
    ],
    'economia': [
        {
            'title': 'Banco Central mantém taxa Selic em 10,75% ao ano',
            'content': 'O Comitê de Política Monetária (Copom) do Banco Central decidiu manter a taxa básica de juros em 10,75% ao ano. A decisão foi unânime e reflete a estratégia de controle inflacionário adotada pela instituição nos últimos meses.',
            'summary': 'Copom mantém Selic estável em decisão unânime',
            'tags': ['selic', 'juros', 'copom', 'economia']
        },
        {
            'title': 'PIB brasileiro cresce 2,1% no terceiro trimestre',
            'content': 'O Produto Interno Bruto (PIB) brasileiro registrou crescimento de 2,1% no terceiro trimestre deste ano, segundo dados do IBGE. O resultado superou expectativas de analistas e consolida tendência de recuperação econômica.',
            'summary': 'PIB supera expectativas com crescimento de 2,1%',
            'tags': ['pib', 'crescimento', 'ibge', 'economia']
        }
    ],
    'tecnologia': [
        {
            'title': 'Nova lei de proteção de dados pessoais entra em vigor',
            'content': 'Entra em vigor hoje a nova regulamentação sobre proteção de dados pessoais no setor público brasileiro. A norma estabelece critérios mais rigorosos para coleta, tratamento e armazenamento de informações dos cidadãos.',
            'summary': 'Proteção de dados no setor público ganha nova regulamentação',
            'tags': ['lgpd', 'dados', 'privacidade', 'digital']
        }
    ],
    'internacional': [
        {
            'title': 'Brasil assina acordo comercial com países do Mercosul',
            'content': 'O Brasil formalizou hoje novo acordo comercial com países membros do Mercosul, visando facilitar o comércio bilateral e reduzir barreiras tarifárias. O acordo deve impactar positivamente o PIB regional.',
            'summary': 'Novo acordo comercial fortalece integração no Mercosul',
            'tags': ['mercosul', 'comercio', 'integracao', 'economia']
        }
    ]
}

def create_categories():
    """Create news categories"""
    categories_data = [
        {'name': 'Política', 'slug': 'politica', 'description': 'Notícias sobre política brasileira'},
        {'name': 'Economia', 'slug': 'economia', 'description': 'Notícias econômicas e financeiras'},
        {'name': 'Tecnologia', 'slug': 'tecnologia', 'description': 'Inovação e tecnologia'},
        {'name': 'Internacional', 'slug': 'internacional', 'description': 'Notícias internacionais'},
        {'name': 'Justiça', 'slug': 'justica', 'description': 'Sistema judiciário brasileiro'},
        {'name': 'Meio Ambiente', 'slug': 'meio-ambiente', 'description': 'Sustentabilidade e meio ambiente'}
    ]
    
    created_categories = []
    for cat_data in categories_data:
        category, created = Category.objects.get_or_create(
            slug=cat_data['slug'],
            defaults={
                'name': cat_data['name'],
                'description': cat_data['description'],
                'is_active': True
            }
        )
        created_categories.append(category)
        if created:
            print(f"✅ Created category: {category.name}")
    
    return created_categories

def create_users_and_profiles():
    """Create demo users with different roles"""
    users_data = [
        {'username': 'admin', 'email': 'admin@jota.news', 'is_staff': True, 'is_superuser': True},
        {'username': 'editor_politica', 'email': 'editor.politica@jota.news', 'is_staff': True},
        {'username': 'editor_economia', 'email': 'editor.economia@jota.news', 'is_staff': True},
        {'username': 'jornalista_1', 'email': 'jornalista1@jota.news', 'is_staff': False},
        {'username': 'jornalista_2', 'email': 'jornalista2@jota.news', 'is_staff': False},
        {'username': 'leitor_premium', 'email': 'premium@example.com', 'is_staff': False},
        {'username': 'leitor_basico', 'email': 'basico@example.com', 'is_staff': False},
    ]
    
    created_users = []
    for user_data in users_data:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'email': user_data['email'],
                'is_staff': user_data['is_staff'],
                'is_superuser': user_data.get('is_superuser', False),
                'first_name': fake.first_name(),
                'last_name': fake.last_name(),
                'is_active': True
            }
        )
        if created:
            user.set_password('demo123')
            user.save()
            print(f"✅ Created user: {user.username}")
        
        # Create user profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'organization': 'JOTA News Demo',
                'position': user.username.replace('_', ' ').title(),
                'department': f'Demo Department',
                'email_notifications': True,
                'sms_notifications': random.choice([True, False]),
                'push_notifications': random.choice([True, False])
            }
        )
        
        created_users.append(user)
    
    return created_users

def create_api_keys(users):
    """Create API keys for different users"""
    api_keys = []
    for user in users[:5]:  # Create API keys for first 5 users
        api_key, created = APIKey.objects.get_or_create(
            user=user,
            name=f'API Key - {user.username}',
            defaults={
                'is_active': True,
                'permissions': ['read', 'write'] if 'editor' in user.username else ['read'],
                'expires_at': timezone.now() + timedelta(days=365)
            }
        )
        if created:
            print(f"✅ Created API key for: {user.username}")
        api_keys.append(api_key)
    
    return api_keys

def create_tags():
    """Create relevant tags"""
    tag_names = [
        'urgente', 'breaking', 'exclusiva', 'investigacao', 'politica', 'economia',
        'justica', 'congresso', 'stf', 'eleicoes', 'orcamento', 'impostos',
        'mercado', 'investimentos', 'inflacao', 'pib', 'copom', 'selic',
        'tecnologia', 'inovacao', 'sustentabilidade', 'meio-ambiente',
        'internacional', 'mercosul', 'comercio', 'diplomacia'
    ]
    
    created_tags = []
    for tag_name in tag_names:
        tag, created = Tag.objects.get_or_create(
            name=tag_name,
            defaults={'is_active': True}
        )
        created_tags.append(tag)
        if created:
            print(f"✅ Created tag: {tag.name}")
    
    return created_tags

def create_news_articles(categories, users, tags):
    """Create realistic news articles"""
    articles_created = 0
    
    for i in range(50):  # Create 50 articles
        # Choose category and corresponding template
        category = random.choice(categories)
        category_slug = category.slug.replace('-', '_')
        
        # Get template or create generic content
        if category_slug in NEWS_TEMPLATES:
            template = random.choice(NEWS_TEMPLATES[category_slug])
            title = template['title']
            content = template['content']
            summary = template['summary']
            article_tags = template['tags']
        else:
            title = f"Notícia importante sobre {category.name.lower()}"
            content = fake.text(max_nb_chars=1000)
            summary = fake.text(max_nb_chars=200)
            article_tags = ['geral', 'noticia']
        
        # Add variation to title and content
        if i > 0:
            title = f"{title} - Atualização {i + 1}"
            content = f"{content}\n\nEsta é uma atualização importante sobre o tema, trazendo novos desenvolvimentos e análises detalhadas."
        
        # Create article
        author = random.choice(users)
        is_urgent = random.choice([True, False, False, False])  # 25% chance of urgent
        
        published_at = timezone.now() - timedelta(
            hours=random.randint(1, 720),  # Up to 30 days ago
            minutes=random.randint(0, 59)
        )
        
        news = News.objects.create(
            title=title,
            content=content,
            summary=summary,
            category=category,
            author=author,
            source=random.choice(['JOTA', 'Agência Brasil', 'Reuters', 'G1']),
            is_published=True,
            is_urgent=is_urgent,
            priority=random.choice(['low', 'medium', 'high', 'urgent']),
            published_at=published_at,
            created_at=published_at,
            metadata={
                'source_url': f'https://example.com/news/{i+1}',
                'reading_time': random.randint(2, 15),
                'word_count': len(content.split()),
                'classification_confidence': random.uniform(0.7, 0.95)
            }
        )
        
        # Add tags
        for tag_name in article_tags:
            tag = next((t for t in tags if t.name == tag_name), None)
            if tag:
                news.tags.add(tag)
        
        # Add some random tags
        random_tags = random.sample(tags, k=random.randint(1, 3))
        for tag in random_tags:
            news.tags.add(tag)
        
        articles_created += 1
        
        if articles_created % 10 == 0:
            print(f"✅ Created {articles_created} news articles")
    
    print(f"✅ Total articles created: {articles_created}")
    return articles_created

def create_notification_channels():
    """Create notification channels"""
    channels_data = [
        {
            'name': 'Email Notifications',
            'channel_type': 'email',
            'config': {
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587,
                'from_email': 'noreply@jota.news'
            }
        },
        {
            'name': 'WhatsApp Business',
            'channel_type': 'whatsapp',
            'config': {
                'api_url': 'https://api.whatsapp.com/send',
                'token': 'demo_token_123'
            }
        },
        {
            'name': 'Slack Notifications',
            'channel_type': 'slack',
            'config': {
                'webhook_url': 'https://hooks.slack.com/demo',
                'channel': '#news-alerts'
            }
        }
    ]
    
    created_channels = []
    for channel_data in channels_data:
        channel, created = NotificationChannel.objects.get_or_create(
            name=channel_data['name'],
            defaults={
                'channel_type': channel_data['channel_type'],
                'config': channel_data['config'],
                'is_active': True,
                'rate_limit': 100
            }
        )
        created_channels.append(channel)
        if created:
            print(f"✅ Created notification channel: {channel.name}")
    
    return created_channels

def create_webhook_sources():
    """Create webhook sources"""
    sources_data = [
        {
            'name': 'Agência Brasil Feed',
            'slug': 'agencia-brasil',
            'source_type': 'rss',
            'config': {
                'feed_url': 'https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml',
                'update_interval': 300
            }
        },
        {
            'name': 'WhatsApp Business Webhook',
            'slug': 'whatsapp-business',
            'source_type': 'whatsapp',
            'config': {
                'verify_token': 'jota_verify_token_123',
                'app_secret': 'demo_app_secret'
            }
        },
        {
            'name': 'Telegram Bot',
            'slug': 'telegram-bot',
            'source_type': 'telegram',
            'config': {
                'bot_token': 'demo_bot_token_456',
                'webhook_url': 'https://api.telegram.org/bot'
            }
        }
    ]
    
    created_sources = []
    for source_data in sources_data:
        source, created = WebhookSource.objects.get_or_create(
            slug=source_data['slug'],
            defaults={
                'name': source_data['name'],
                'source_type': source_data['source_type'],
                'config': source_data['config'],
                'is_active': True,
                'rate_limit': 1000
            }
        )
        created_sources.append(source)
        if created:
            print(f"✅ Created webhook source: {source.name}")
    
    return created_sources

def main():
    """Main function to generate all demo data"""
    print("🚀 Starting JOTA News System Demo Data Generation...")
    print("=" * 60)
    
    try:
        # Create categories
        print("\n📁 Creating categories...")
        categories = create_categories()
        
        # Create users and profiles
        print("\n👥 Creating users and profiles...")
        users = create_users_and_profiles()
        
        # Create API keys
        print("\n🔑 Creating API keys...")
        api_keys = create_api_keys(users)
        
        # Create tags
        print("\n🏷️ Creating tags...")
        tags = create_tags()
        
        # Create news articles
        print("\n📰 Creating news articles...")
        articles_count = create_news_articles(categories, users, tags)
        
        # Create notification channels
        print("\n📧 Creating notification channels...")
        channels = create_notification_channels()
        
        # Create webhook sources
        print("\n🔗 Creating webhook sources...")
        sources = create_webhook_sources()
        
        print("\n" + "=" * 60)
        print("✅ Demo data generation completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Categories: {len(categories)}")
        print(f"   - Users: {len(users)}")
        print(f"   - API Keys: {len(api_keys)}")
        print(f"   - Tags: {len(tags)}")
        print(f"   - News Articles: {articles_count}")
        print(f"   - Notification Channels: {len(channels)}")
        print(f"   - Webhook Sources: {len(sources)}")
        print("\n🎯 System is ready for demonstration!")
        
    except Exception as e:
        print(f"❌ Error generating demo data: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()