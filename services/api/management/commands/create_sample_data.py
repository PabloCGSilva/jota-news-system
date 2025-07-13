"""
Django management command to create sample data for demo purposes.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.news.models import Category, Subcategory, News, Tag
from apps.webhooks.models import WebhookSource
from apps.notifications.models import NotificationChannel, NotificationSubscription
from apps.authentication.models import APIKey
from django.utils import timezone
import random
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample data for JOTA News System demo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new sample data'
        )
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create'
        )
        parser.add_argument(
            '--news',
            type=int,
            default=50,
            help='Number of news articles to create'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_data()
        
        self.create_categories()
        self.create_tags()
        self.create_users(options['users'])
        self.create_webhook_sources()
        self.create_notification_channels()
        self.create_news_articles(options['news'])
        self.create_subscriptions()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample data with {options["users"]} users and {options["news"]} news articles'
            )
        )

    def clear_data(self):
        """Clear existing data."""
        self.stdout.write('Clearing existing data...')
        
        # Clear in order to respect foreign key constraints
        News.objects.all().delete()
        NotificationSubscription.objects.all().delete()
        NotificationChannel.objects.all().delete()
        WebhookSource.objects.all().delete()
        APIKey.objects.all().delete()
        Tag.objects.all().delete()
        Subcategory.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        
        self.stdout.write(self.style.SUCCESS('Data cleared successfully'))

    def create_categories(self):
        """Create sample categories and subcategories."""
        self.stdout.write('Creating categories...')
        
        categories_data = [
            {
                'name': 'Poder',
                'slug': 'poder',
                'description': 'Notícias sobre os três poderes da República',
                'keywords': ['governo', 'política', 'congresso', 'judiciário', 'executivo'],
                'subcategories': [
                    {
                        'name': 'Executivo',
                        'slug': 'executivo',
                        'description': 'Poder Executivo Federal',
                        'keywords': ['presidente', 'ministros', 'governo federal']
                    },
                    {
                        'name': 'Legislativo',
                        'slug': 'legislativo',
                        'description': 'Congresso Nacional',
                        'keywords': ['câmara', 'senado', 'deputados', 'senadores']
                    },
                    {
                        'name': 'Judiciário',
                        'slug': 'judiciario',
                        'description': 'Poder Judiciário',
                        'keywords': ['stf', 'stj', 'tribunais', 'juízes']
                    }
                ]
            },
            {
                'name': 'Tributos',
                'slug': 'tributos',
                'description': 'Tributação e impostos',
                'keywords': ['impostos', 'receita federal', 'tributação', 'reforma tributária'],
                'subcategories': [
                    {
                        'name': 'Impostos Federais',
                        'slug': 'impostos-federais',
                        'description': 'Impostos da União',
                        'keywords': ['ir', 'ipi', 'cofins', 'pis']
                    },
                    {
                        'name': 'Reforma Tributária',
                        'slug': 'reforma-tributaria',
                        'description': 'Mudanças no sistema tributário',
                        'keywords': ['reforma', 'simplificação', 'iva']
                    }
                ]
            },
            {
                'name': 'Saúde',
                'slug': 'saude',
                'description': 'Saúde pública e regulamentação',
                'keywords': ['saúde pública', 'sus', 'anvisa', 'medicina'],
                'subcategories': [
                    {
                        'name': 'SUS',
                        'slug': 'sus',
                        'description': 'Sistema Único de Saúde',
                        'keywords': ['sus', 'atendimento', 'hospitais públicos']
                    },
                    {
                        'name': 'Regulamentação',
                        'slug': 'regulamentacao',
                        'description': 'Regulamentação em saúde',
                        'keywords': ['anvisa', 'medicamentos', 'regulação']
                    }
                ]
            },
            {
                'name': 'Trabalhista',
                'slug': 'trabalhista',
                'description': 'Direito do trabalho e previdência',
                'keywords': ['trabalho', 'previdência', 'emprego', 'sindicatos'],
                'subcategories': [
                    {
                        'name': 'Previdência',
                        'slug': 'previdencia',
                        'description': 'Previdência Social',
                        'keywords': ['inss', 'aposentadoria', 'benefícios']
                    },
                    {
                        'name': 'Emprego',
                        'slug': 'emprego',
                        'description': 'Mercado de trabalho',
                        'keywords': ['emprego', 'desemprego', 'carteira assinada']
                    }
                ]
            },
            {
                'name': 'Economia',
                'slug': 'economia',
                'description': 'Economia e finanças',
                'keywords': ['economia', 'inflação', 'juros', 'pib'],
                'subcategories': [
                    {
                        'name': 'Política Monetária',
                        'slug': 'politica-monetaria',
                        'description': 'Banco Central e política monetária',
                        'keywords': ['bacen', 'selic', 'inflação']
                    },
                    {
                        'name': 'Mercado Financeiro',
                        'slug': 'mercado-financeiro',
                        'description': 'Mercados financeiros',
                        'keywords': ['bolsa', 'investimentos', 'bancos']
                    }
                ]
            }
        ]
        
        for cat_data in categories_data:
            subcats = cat_data.pop('subcategories')
            category, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            
            for sub_data in subcats:
                Subcategory.objects.get_or_create(
                    category=category,
                    slug=sub_data['slug'],
                    defaults=sub_data
                )
        
        self.stdout.write(self.style.SUCCESS(f'Created {Category.objects.count()} categories'))

    def create_tags(self):
        """Create sample tags."""
        self.stdout.write('Creating tags...')
        
        tags_data = [
            'breaking-news', 'última-hora', 'economia', 'política', 'saúde',
            'educação', 'meio-ambiente', 'tecnologia', 'justiça', 'congresso',
            'stf', 'ministérios', 'reforma', 'eleições', 'covid-19',
            'vacina', 'impostos', 'inflação', 'desemprego', 'pib'
        ]
        
        for tag_name in tags_data:
            Tag.objects.get_or_create(
                slug=tag_name,
                defaults={
                    'name': tag_name.replace('-', ' ').title(),
                    'description': f'Tag para {tag_name}',
                    'usage_count': random.randint(1, 50)
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {Tag.objects.count()} tags'))

    def create_users(self, count):
        """Create sample users."""
        self.stdout.write(f'Creating {count} users...')
        
        users_data = [
            {'username': 'jornalista1', 'email': 'jornalista1@jota.news', 'first_name': 'Ana', 'last_name': 'Silva'},
            {'username': 'jornalista2', 'email': 'jornalista2@jota.news', 'first_name': 'Carlos', 'last_name': 'Santos'},
            {'username': 'editor1', 'email': 'editor1@jota.news', 'first_name': 'Maria', 'last_name': 'Oliveira'},
            {'username': 'editor2', 'email': 'editor2@jota.news', 'first_name': 'João', 'last_name': 'Costa'},
            {'username': 'revisor1', 'email': 'revisor1@jota.news', 'first_name': 'Paula', 'last_name': 'Ferreira'},
        ]
        
        for i, user_data in enumerate(users_data[:count]):
            if i < len(users_data):
                user, created = User.objects.get_or_create(
                    username=user_data['username'],
                    defaults={
                        **user_data,
                        'password': 'pbkdf2_sha256$600000$test$hash',  # 'demo123'
                        'is_active': True,
                        'is_staff': i < 2,  # First 2 users are staff
                        'bio': f'Profissional de {user_data["first_name"]} {user_data["last_name"]}',
                        'timezone': 'America/Sao_Paulo',
                        'language': 'pt-br'
                    }
                )
                
                # Create API key for some users
                if i < 3:
                    APIKey.objects.get_or_create(
                        user=user,
                        name=f'API Key {user.username}',
                        defaults={'key': f'api-key-{user.username}-{i}'}
                    )
        
        # Create additional generic users
        for i in range(len(users_data), count):
            User.objects.get_or_create(
                username=f'user{i}',
                defaults={
                    'email': f'user{i}@example.com',
                    'first_name': f'User{i}',
                    'last_name': 'Demo',
                    'password': 'pbkdf2_sha256$600000$test$hash',
                    'is_active': True,
                    'bio': f'Demo user {i}',
                    'timezone': 'America/Sao_Paulo',
                    'language': 'pt-br'
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {User.objects.filter(is_superuser=False).count()} users'))

    def create_webhook_sources(self):
        """Create sample webhook sources."""
        self.stdout.write('Creating webhook sources...')
        
        sources_data = [
            {
                'name': 'Agência Brasil',
                'slug': 'agencia-brasil',
                'description': 'Webhook da Agência Brasil',
                'url': 'https://agenciabrasil.ebc.com.br/webhook',
                'secret_key': 'agencia-brasil-secret-key',
                'content_type': 'application/json',
                'is_active': True
            },
            {
                'name': 'Folha de S.Paulo',
                'slug': 'folha-sp',
                'description': 'Webhook da Folha de S.Paulo',
                'url': 'https://www1.folha.uol.com.br/webhook',
                'secret_key': 'folha-sp-secret-key',
                'content_type': 'application/json',
                'is_active': True
            },
            {
                'name': 'G1 Notícias',
                'slug': 'g1-noticias',
                'description': 'Webhook do G1',
                'url': 'https://g1.globo.com/webhook',
                'secret_key': 'g1-noticias-secret-key',
                'content_type': 'application/json',
                'is_active': True
            },
            {
                'name': 'Congresso em Foco',
                'slug': 'congresso-foco',
                'description': 'Webhook do Congresso em Foco',
                'url': 'https://congressoemfoco.com.br/webhook',
                'secret_key': 'congresso-foco-secret-key',
                'content_type': 'application/json',
                'is_active': True
            }
        ]
        
        for source_data in sources_data:
            WebhookSource.objects.get_or_create(
                slug=source_data['slug'],
                defaults=source_data
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {WebhookSource.objects.count()} webhook sources'))

    def create_notification_channels(self):
        """Create sample notification channels."""
        self.stdout.write('Creating notification channels...')
        
        channels_data = [
            {
                'name': 'Email Principal',
                'channel_type': 'email',
                'description': 'Canal principal de email',
                'config': {
                    'smtp_server': 'smtp.jota.news',
                    'smtp_port': 587,
                    'username': 'notifications@jota.news',
                    'use_tls': True
                },
                'is_active': True,
                'is_default': True
            },
            {
                'name': 'WhatsApp Business',
                'channel_type': 'whatsapp',
                'description': 'Canal WhatsApp Business',
                'config': {
                    'api_url': 'https://graph.facebook.com/v18.0',
                    'phone_number_id': '123456789',
                    'verify_token': 'whatsapp-verify-token'
                },
                'is_active': True
            },
            {
                'name': 'Slack JOTA',
                'channel_type': 'slack',
                'description': 'Canal Slack da equipe JOTA',
                'config': {
                    'webhook_url': 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX',
                    'channel': '#noticias',
                    'username': 'JOTA Bot'
                },
                'is_active': True
            },
            {
                'name': 'SMS Brasil',
                'channel_type': 'sms',
                'description': 'Canal SMS para notificações urgentes',
                'config': {
                    'provider': 'zenvia',
                    'api_key': 'sms-api-key',
                    'sender': 'JOTA'
                },
                'is_active': True
            }
        ]
        
        for channel_data in channels_data:
            NotificationChannel.objects.get_or_create(
                name=channel_data['name'],
                defaults=channel_data
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {NotificationChannel.objects.count()} notification channels'))

    def create_news_articles(self, count):
        """Create sample news articles."""
        self.stdout.write(f'Creating {count} news articles...')
        
        categories = list(Category.objects.all())
        subcategories = list(Subcategory.objects.all())
        tags = list(Tag.objects.all())
        
        sample_articles = [
            {
                'title': 'Congresso aprova nova lei de transparência pública',
                'content': 'O Congresso Nacional aprovou hoje uma nova lei que amplia os mecanismos de transparência pública, obrigando órgãos governamentais a divulgar informações de forma mais detalhada e acessível aos cidadãos.',
                'summary': 'Nova lei amplia transparência pública no governo',
                'source': 'Agência Brasil',
                'author': 'Reporter Legal',
                'is_urgent': False
            },
            {
                'title': 'STF decide sobre marco temporal das terras indígenas',
                'content': 'O Supremo Tribunal Federal julgou hoje a questão do marco temporal para demarcação de terras indígenas, em decisão que pode impactar milhares de comunidades pelo país.',
                'summary': 'STF julga marco temporal indígena',
                'source': 'Folha de S.Paulo',
                'author': 'Correspondente Judiciário',
                'is_urgent': True
            },
            {
                'title': 'Receita Federal lança novo sistema de declaração de IR',
                'content': 'A Receita Federal apresentou hoje o novo sistema para declaração do Imposto de Renda, que promete simplificar o processo e reduzir erros na declaração.',
                'summary': 'Novo sistema simplifica declaração de IR',
                'source': 'G1 Notícias',
                'author': 'Especialista Tributário',
                'is_urgent': False
            },
            {
                'title': 'Ministério da Saúde anuncia nova campanha de vacinação',
                'content': 'O Ministério da Saúde anunciou hoje uma nova campanha nacional de vacinação contra a gripe, que começará na próxima semana em todo o território nacional.',
                'summary': 'Nova campanha de vacinação contra gripe',
                'source': 'Agência Brasil',
                'author': 'Repórter Saúde',
                'is_urgent': False
            },
            {
                'title': 'Senado debate reforma trabalhista complementar',
                'content': 'O Senado Federal iniciou hoje os debates sobre uma reforma trabalhista complementar, que visa ajustar pontos controversos da legislação atual.',
                'summary': 'Senado debate ajustes na legislação trabalhista',
                'source': 'Congresso em Foco',
                'author': 'Correspondente Legislativo',
                'is_urgent': False
            }
        ]
        
        created_count = 0
        for i in range(count):
            if i < len(sample_articles):
                article_data = sample_articles[i]
            else:
                article_data = {
                    'title': f'Notícia de exemplo {i+1}',
                    'content': f'Conteúdo da notícia {i+1}. Esta é uma notícia de exemplo criada automaticamente para demonstrar o funcionamento do sistema.',
                    'summary': f'Resumo da notícia {i+1}',
                    'source': random.choice(['Agência Brasil', 'Folha de S.Paulo', 'G1 Notícias', 'Congresso em Foco']),
                    'author': random.choice(['Reporter A', 'Jornalista B', 'Correspondente C', 'Especialista D']),
                    'is_urgent': random.choice([True, False, False, False])  # 25% chance of urgent
                }
            
            # Random published date within last 30 days
            published_at = timezone.now() - timedelta(days=random.randint(0, 30))
            
            news = News.objects.create(
                title=article_data['title'],
                content=article_data['content'],
                summary=article_data['summary'],
                source=article_data['source'],
                source_url=f'https://example.com/news/{i+1}',
                author=article_data['author'],
                category=random.choice(categories),
                subcategory=random.choice(subcategories),
                published_at=published_at,
                is_urgent=article_data['is_urgent'],
                is_published=True,
                is_processed=True,
                category_confidence=random.uniform(0.7, 1.0),
                urgency_confidence=random.uniform(0.1, 0.9)
            )
            
            # Add random tags
            article_tags = random.sample(tags, random.randint(1, 4))
            news.tags.set(article_tags)
            
            created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {created_count} news articles'))

    def create_subscriptions(self):
        """Create sample notification subscriptions."""
        self.stdout.write('Creating notification subscriptions...')
        
        users = User.objects.filter(is_superuser=False)[:5]
        channels = NotificationChannel.objects.all()
        categories = Category.objects.all()
        
        for user in users:
            for channel in channels[:2]:  # Subscribe to first 2 channels
                subscription = NotificationSubscription.objects.create(
                    user=user,
                    channel=channel,
                    destination=user.email if channel.channel_type == 'email' else f'+5511999{user.id:06d}',
                    min_priority=random.choice(['low', 'medium', 'high']),
                    urgent_only=random.choice([True, False]),
                    is_active=True
                )
                
                # Subscribe to random categories
                sub_categories = random.sample(list(categories), random.randint(1, 3))
                subscription.categories.set(sub_categories)
        
        self.stdout.write(self.style.SUCCESS(f'Created {NotificationSubscription.objects.count()} subscriptions'))