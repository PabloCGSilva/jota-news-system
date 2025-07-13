"""
Test settings for JOTA News System.
"""
from .settings import *

# Test database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations in tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Fast password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable cache in tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Use local memory for Celery in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Test email backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable logging in tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Test media/static paths
MEDIA_ROOT = '/tmp/test_media'
STATIC_ROOT = '/tmp/test_static'

# Mock external services
WHATSAPP_API_URL = 'http://mock-whatsapp-api.local'
WHATSAPP_ACCESS_TOKEN = 'test_token'
WHATSAPP_PHONE_NUMBER_ID = 'test_phone_id'
WHATSAPP_VERIFY_TOKEN = 'test_verify_token'

# Test-specific settings
SECRET_KEY = 'test-secret-key-not-for-production'
DEBUG = True
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# Disable external requests
REDIS_URL = 'redis://mock-redis.local:6379/0'