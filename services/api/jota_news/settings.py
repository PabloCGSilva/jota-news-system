"""
Django settings for jota_news project.
"""
import os
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-local-development-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0,api', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    'django_prometheus',
    'django_extensions',
]

LOCAL_APPS = [
    'apps.authentication',
    'apps.news',
    'apps.webhooks',
    'apps.classification',
    'apps.notifications',
    'apps.demo',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'jota_news.middleware.RequestLoggingMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'jota_news.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'jota_news.wsgi.application'

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='postgresql://postgres:postgres@localhost:5432/jota_news'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'authentication.User'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'apps.authentication.drf_authentication.APIKeyAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10000/hour',  # Increased for testing and demos
        'user': '10000/hour'   # Increased for testing and demos
    }
}

# Spectacular (OpenAPI) Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'JOTA News API',
    'DESCRIPTION': 'API for JOTA News Processing System',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {'name': 'JOTA Development Team'},
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
}

# JWT Configuration
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}

# Redis Configuration
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'jota_news',
        'TIMEOUT': 300,
    }
}

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE


# WhatsApp configuration removed - external META Business API dependency not needed

# NLTK Configuration
import os
import nltk
NLTK_DATA_PATH = os.environ.get('NLTK_DATA', '/app/nltk_data')
if NLTK_DATA_PATH not in nltk.data.path:
    nltk.data.path.insert(0, NLTK_DATA_PATH)

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8080',
]

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'jota_news': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Create logs directory
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Email Configuration - Console backend for out-of-the-box demo
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@jota-news-demo.local')

# News Classification Configuration
CLASSIFICATION_CATEGORIES = {
    'poder': ['governo', 'política', 'congresso', 'executivo', 'legislativo', 'judiciário'],
    'tributos': ['impostos', 'receita federal', 'tributação', 'reforma tributária'],
    'saúde': ['saúde pública', 'medicina', 'hospitais', 'anvisa'],
    'trabalhista': ['trabalho', 'previdência', 'emprego', 'sindicatos'],
}

# News Processing Configuration
NEWS_PROCESSING_BATCH_SIZE = 100
NEWS_URGENT_KEYWORDS = ['urgente', 'breaking', 'última hora', 'agora']
NEWS_MAX_TITLE_LENGTH = 200
NEWS_MAX_CONTENT_LENGTH = 10000

# DRF Spectacular (OpenAPI Documentation)
SPECTACULAR_SETTINGS = {
    'TITLE': 'JOTA News System API',
    'DESCRIPTION': '''
    A comprehensive news processing and notification system built with Django REST Framework.
    
    ## Features
    - **News Management**: Complete CRUD operations for news articles
    - **Webhook Integration**: Receive news from external sources with authentication
    - **AI Classification**: Automatic news categorization using NLP
    - **Multi-Channel Notifications**: WhatsApp, Email, Slack, SMS notifications
    - **User Subscriptions**: Flexible subscription system with filtering
    
    ## Authentication
    This API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:
    ```
    Authorization: Bearer <your_token>
    ```
    
    ## Rate Limiting
    API endpoints are rate limited to prevent abuse. Current limits:
    - Authenticated users: 1000 requests/hour
    - Anonymous users: 100 requests/hour
    - Webhook endpoints: Configurable per source
    
    ## Webhooks
    External systems can send news via webhooks to `/api/v1/webhooks/receive/{source_name}/`
    Webhook signature verification is supported using HMAC-SHA256.
    
    ## Notification Channels
    Supported notification channels:
    - **WhatsApp**: WhatsApp Business API integration
    - **Email**: SMTP email notifications
    - **Slack**: Slack webhook notifications  
    - **SMS**: SMS gateway integration
    - **Webhook**: HTTP webhook notifications
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'CONTACT': {
        'name': 'JOTA Development Team',
        'email': 'dev@jota.news',
        'url': 'https://jota.news'
    },
    'LICENSE': {
        'name': 'MIT License',
        'url': 'https://opensource.org/licenses/MIT'
    },
    'SERVERS': [
        {'url': 'http://localhost:8000', 'description': 'Local Development Server'},
        {'url': 'https://api.jota.news', 'description': 'Production Server'},
    ],
    'TAGS': [
        {
            'name': 'Authentication',
            'description': 'JWT token authentication and user management'
        },
        {
            'name': 'News',
            'description': 'News articles, categories, and tags management'
        },
        {
            'name': 'Webhooks', 
            'description': 'Webhook sources and processing for external integrations'
        },
        {
            'name': 'Classification',
            'description': 'AI-powered news classification and rules management'
        },
        {
            'name': 'Notifications',
            'description': 'Multi-channel notification system and subscriptions'
        },
        {
            'name': 'Monitoring',
            'description': 'System health, metrics, and operational endpoints'
        }
    ],
    'EXTERNAL_DOCS': {
        'description': 'JOTA News System Documentation',
        'url': 'https://docs.jota.news'
    },
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
        'displayRequestDuration': True,
        'docExpansion': 'list',
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
        'tryItOutEnabled': True,
    },
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'hideHostname': False,
        'hideLoading': False,
        'hideSchemaPattern': True,
        'expandResponses': 'all',
        'pathInMiddlePanel': True,
        'theme': {
            'colors': {
                'primary': {'main': '#1976d2'}
            }
        }
    }
}