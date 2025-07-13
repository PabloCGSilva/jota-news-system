"""
Management command to create sample data for testing and demonstration.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from apps.news.models import Category, Tag, News
from apps.webhooks.models import WebhookSource
from apps.authentication.models import APIKey
import random
import uuid

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample data for testing and demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--articles',
            type=int,
            default=10,
            help='Number of sample articles to create'
        )
        parser.add_argument(
            '--categories',
            type=int,
            default=5,
            help='Number of sample categories to create'
        )
        parser.add_argument(
            '--users',
            type=int,
            default=3,
            help='Number of sample users to create'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Creating sample data for JOTA News System...')
        )

        # Create sample categories
        categories_created = self.create_categories(options['categories'])
        
        # Create sample tags
        tags_created = self.create_tags()
        
        # Create sample users
        users_created = self.create_users(options['users'])
        
        # Create sample articles
        articles_created = self.create_articles(options['articles'])
        
        # Create webhook sources
        webhook_sources_created = self.create_webhook_sources()

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSample data created successfully!\n'
                f'- Categories: {categories_created}\n'
                f'- Tags: {tags_created}\n'
                f'- Users: {users_created}\n'
                f'- Articles: {articles_created}\n'
                f'- Webhook Sources: {webhook_sources_created}'
            )
        )

    def create_categories(self, count):
        sample_categories = [
            ('Technology', 'Latest technology news and innovations'),
            ('Politics', 'Political news and government updates'),
            ('Sports', 'Sports news and match results'),
            ('Business', 'Business and financial news'),
            ('Health', 'Health and medical news'),
            ('Science', 'Scientific discoveries and research'),
            ('Entertainment', 'Entertainment and celebrity news'),
            ('Environment', 'Environmental and climate news'),
        ]
        
        created = 0
        for i, (name, description) in enumerate(sample_categories[:count]):
            category, was_created = Category.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            if was_created:
                created += 1
                self.stdout.write(f'Created category: {name}')
        
        return created

    def create_tags(self):
        sample_tags = [
            'breaking', 'urgent', 'analysis', 'exclusive', 'interview',
            'investigation', 'opinion', 'review', 'research', 'innovation',
            'startup', 'AI', 'blockchain', 'climate', 'election'
        ]
        
        created = 0
        for tag_name in sample_tags:
            tag, was_created = Tag.objects.get_or_create(name=tag_name)
            if was_created:
                created += 1
                self.stdout.write(f'Created tag: {tag_name}')
        
        return created

    def create_users(self, count):
        sample_users = [
            ('john.doe', 'john@example.com', 'John Doe'),
            ('jane.smith', 'jane@example.com', 'Jane Smith'),
            ('mike.johnson', 'mike@example.com', 'Mike Johnson'),
            ('sarah.wilson', 'sarah@example.com', 'Sarah Wilson'),
            ('david.brown', 'david@example.com', 'David Brown'),
        ]
        
        created = 0
        for i, (username, email, full_name) in enumerate(sample_users[:count]):
            user, was_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': full_name.split()[0],
                    'last_name': full_name.split()[1],
                    'is_active': True
                }
            )
            if was_created:
                user.set_password('demo123')
                user.save()
                created += 1
                self.stdout.write(f'Created user: {username}')
        
        return created

    def create_articles(self, count):
        sample_articles = [
            {
                'title': 'Revolutionary AI Technology Unveiled at Tech Conference',
                'content': 'A groundbreaking artificial intelligence system was demonstrated today at the annual technology conference. The new system promises to revolutionize how we interact with computers and automate complex tasks across multiple industries.',
                'source': 'Tech Daily',
                'author': 'Tech Reporter',
            },
            {
                'title': 'Economic Growth Reaches New Heights This Quarter',
                'content': 'The latest economic indicators show unprecedented growth in the technology and renewable energy sectors. Analysts predict continued expansion as new policies support innovation and sustainable development.',
                'source': 'Economic Times',
                'author': 'Financial Analyst',
            },
            {
                'title': 'Championship Finals Set for This Weekend',
                'content': 'The highly anticipated championship finals are scheduled for this weekend, with two top teams competing for the title. Ticket sales have broken records, and millions are expected to watch the broadcast.',
                'source': 'Sports Central',
                'author': 'Sports Writer',
            },
            {
                'title': 'New Environmental Protection Measures Announced',
                'content': 'Government officials announced comprehensive new measures to protect the environment and combat climate change. The initiatives include investment in renewable energy and stricter regulations on emissions.',
                'source': 'Green News',
                'author': 'Environmental Reporter',
            },
            {
                'title': 'Medical Breakthrough in Cancer Research',
                'content': 'Researchers have announced a significant breakthrough in cancer treatment, with new therapy showing promising results in clinical trials. The treatment could potentially help millions of patients worldwide.',
                'source': 'Medical Journal',
                'author': 'Health Correspondent',
            },
        ]
        
        categories = list(Category.objects.all())
        tags = list(Tag.objects.all())
        
        if not categories:
            self.stdout.write(
                self.style.WARNING('No categories available. Creating articles without categories.')
            )
        
        created = 0
        for i in range(count):
            article_data = sample_articles[i % len(sample_articles)]
            
            # Create unique title
            title = f"{article_data['title']} - {i+1}"
            
            article, was_created = News.objects.get_or_create(
                title=title,
                defaults={
                    'content': article_data['content'],
                    'source': article_data['source'],
                    'author': article_data['author'],
                    'category': random.choice(categories) if categories else None,
                    'is_published': True,
                    'is_urgent': random.choice([True, False]),
                    'external_id': f'sample-{i+1}-{str(uuid.uuid4())[:8]}'
                }
            )
            
            if was_created:
                # Add random tags
                if tags:
                    selected_tags = random.sample(tags, min(3, len(tags)))
                    article.tags.set(selected_tags)
                
                created += 1
                self.stdout.write(f'Created article: {title}')
        
        return created

    def create_webhook_sources(self):
        sample_sources = [
            {
                'name': 'external-news-api',
                'description': 'External news API integration',
                'endpoint_url': 'http://localhost:8000/api/v1/webhooks/receive/external-news-api/',
                'secret_key': 'demo-secret-key-123',
            },
            {
                'name': 'demo-source',
                'description': 'Demo webhook source for testing',
                'endpoint_url': 'http://localhost:8000/api/v1/webhooks/receive/demo-source/',
                'secret_key': 'demo-webhook-secret',
            },
        ]
        
        created = 0
        for source_data in sample_sources:
            source, was_created = WebhookSource.objects.get_or_create(
                name=source_data['name'],
                defaults=source_data
            )
            if was_created:
                created += 1
                self.stdout.write(f'Created webhook source: {source_data["name"]}')
        
        return created