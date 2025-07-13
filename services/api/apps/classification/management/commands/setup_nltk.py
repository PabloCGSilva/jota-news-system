"""
Django management command to setup NLTK data.
"""
import os
import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Download and setup required NLTK data for Portuguese news classification'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-download even if data already exists',
        )
        parser.add_argument(
            '--data-dir',
            type=str,
            help='Custom directory for NLTK data (default: /app/nltk_data)',
            default='/app/nltk_data'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.HTTP_INFO('🔧 Setting up NLTK for Portuguese news classification...')
        )
        
        try:
            import nltk
        except ImportError:
            raise CommandError(
                "NLTK is not installed. Please install it with: pip install nltk"
            )

        # Set NLTK data path
        nltk_data_dir = options['data_dir']
        if not os.path.exists(nltk_data_dir):
            os.makedirs(nltk_data_dir, exist_ok=True)
        
        # Add to NLTK data path
        if nltk_data_dir not in nltk.data.path:
            nltk.data.path.insert(0, nltk_data_dir)

        self.stdout.write(f"📁 NLTK data directory: {nltk_data_dir}")

        # Required NLTK datasets for Portuguese classification
        required_datasets = [
            ('punkt', 'Punkt tokenizer models'),
            ('stopwords', 'Stopwords corpus'),
        ]

        success_count = 0
        total_count = len(required_datasets)

        for dataset_name, description in required_datasets:
            self.stdout.write(f"📦 Downloading {description}...")
            
            try:
                # Check if already exists (unless forced)
                if not options['force']:
                    try:
                        nltk.data.find(f'tokenizers/{dataset_name}' if dataset_name == 'punkt' else f'corpora/{dataset_name}')
                        self.stdout.write(
                            self.style.SUCCESS(f"✓ {description} already exists (use --force to re-download)")
                        )
                        success_count += 1
                        continue
                    except LookupError:
                        pass  # Dataset doesn't exist, proceed to download

                # Download the dataset
                result = nltk.download(dataset_name, download_dir=nltk_data_dir, quiet=False)
                
                if result:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ {description} downloaded successfully")
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f"✗ Failed to download {description}")
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error downloading {description}: {str(e)}")
                )

        # Verify installation
        self.stdout.write(f"\n🔍 Verifying NLTK setup...")
        
        try:
            # Test Portuguese stopwords
            from nltk.corpus import stopwords
            pt_stopwords = stopwords.words('portuguese')
            self.stdout.write(
                self.style.SUCCESS(f"✓ Portuguese stopwords loaded ({len(pt_stopwords)} words)")
            )
            
            # Test tokenization
            from nltk.tokenize import word_tokenize
            test_tokens = word_tokenize("Esta é uma notícia de teste.", language='portuguese')
            self.stdout.write(
                self.style.SUCCESS(f"✓ Portuguese tokenization working (test: {test_tokens})")
            )
            
            # Test stemmer
            from nltk.stem import PorterStemmer
            stemmer = PorterStemmer()
            test_stem = stemmer.stem('tecnologia')
            self.stdout.write(
                self.style.SUCCESS(f"✓ Porter stemmer working (tecnologia → {test_stem})")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ NLTK verification failed: {str(e)}")
            )
            raise CommandError("NLTK setup verification failed")

        # Display summary
        self.stdout.write(f"\n📊 Setup Summary:")
        self.stdout.write(f"   Downloaded: {success_count}/{total_count} datasets")
        self.stdout.write(f"   Data directory: {nltk_data_dir}")
        
        if success_count == total_count:
            self.stdout.write(
                self.style.SUCCESS("\n🎉 NLTK setup completed successfully!")
            )
            self.stdout.write(
                "📝 NLTK is now ready for Portuguese news classification."
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"\n⚠️  Partial setup: {success_count}/{total_count} datasets")
            )

        # Instructions for Docker environments
        self.stdout.write(f"\n💡 For Docker deployment:")
        self.stdout.write(f"   Add this line to your Dockerfile:")
        self.stdout.write(f"   RUN python manage.py setup_nltk")