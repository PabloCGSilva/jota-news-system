"""
Custom schema configurations for OpenAPI documentation.
"""
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


def preprocessing_filter_spec(endpoints):
    """
    Filter and customize the OpenAPI spec before generation.
    """
    filtered = []
    for path, path_regex, method, callback in endpoints:
        # Skip Django admin endpoints
        if path.startswith('/admin/'):
            continue
        
        # Skip internal Django endpoints
        if any(skip in path for skip in ['__debug__', '_debug_toolbar']):
            continue
            
        filtered.append((path, path_regex, method, callback))
    
    return filtered


def postprocessing_hook(result, generator, request, public):
    """
    Modify the generated OpenAPI schema after generation.
    """
    # Add custom security schemes
    if 'components' not in result:
        result['components'] = {}
    
    if 'securitySchemes' not in result['components']:
        result['components']['securitySchemes'] = {}
    
    # Add JWT Bearer auth
    result['components']['securitySchemes']['bearerAuth'] = {
        'type': 'http',
        'scheme': 'bearer',
        'bearerFormat': 'JWT',
        'description': 'JWT token obtained from /api/v1/auth/token/ endpoint'
    }
    
    # Add webhook signature auth
    result['components']['securitySchemes']['webhookSignature'] = {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-Hub-Signature-256',
        'description': 'HMAC-SHA256 signature for webhook verification'
    }
    
    # Add global security requirement
    if 'security' not in result:
        result['security'] = []
    
    # Add common response schemas
    if 'schemas' not in result['components']:
        result['components']['schemas'] = {}
    
    result['components']['schemas']['ErrorResponse'] = {
        'type': 'object',
        'properties': {
            'error': {
                'type': 'string',
                'description': 'Error message'
            },
            'details': {
                'type': 'object',
                'description': 'Additional error details',
                'additionalProperties': True
            },
            'code': {
                'type': 'string',
                'description': 'Error code'
            }
        },
        'required': ['error']
    }
    
    result['components']['schemas']['SuccessResponse'] = {
        'type': 'object',
        'properties': {
            'message': {
                'type': 'string',
                'description': 'Success message'
            },
            'data': {
                'type': 'object',
                'description': 'Response data',
                'additionalProperties': True
            }
        },
        'required': ['message']
    }
    
    result['components']['schemas']['PaginatedResponse'] = {
        'type': 'object',
        'properties': {
            'count': {
                'type': 'integer',
                'description': 'Total number of items'
            },
            'next': {
                'type': 'string',
                'format': 'uri',
                'nullable': True,
                'description': 'URL for the next page'
            },
            'previous': {
                'type': 'string',
                'format': 'uri', 
                'nullable': True,
                'description': 'URL for the previous page'
            },
            'results': {
                'type': 'array',
                'items': {
                    'type': 'object'
                },
                'description': 'Array of items for current page'
            }
        },
        'required': ['count', 'results']
    }
    
    # Add webhook examples
    result['components']['examples'] = {
        'NewsWebhookExample': {
            'summary': 'News webhook payload example',
            'description': 'Example payload for receiving news via webhook',
            'value': {
                'title': 'Breaking: New Technology Announced',
                'content': 'Detailed article content about the new technology...',
                'source': 'Tech News Portal',
                'author': 'John Doe',
                'category_hint': 'technology',
                'tags': ['technology', 'innovation', 'announcement'],
                'is_urgent': False,
                'published_at': '2024-01-15T10:30:00Z',
                'metadata': {
                    'original_url': 'https://technews.com/article/123',
                    'language': 'pt-BR'
                }
            }
        },
        'WhatsAppWebhookExample': {
            'summary': 'WhatsApp webhook payload example',
            'description': 'Example payload from WhatsApp Business API',
            'value': {
                'object': 'whatsapp_business_account',
                'entry': [{
                    'id': 'entry_id',
                    'changes': [{
                        'value': {
                            'messaging_product': 'whatsapp',
                            'metadata': {
                                'phone_number_id': 'phone_id'
                            },
                            'messages': [{
                                'id': 'message_id',
                                'from': '5511999999999',
                                'timestamp': '1234567890',
                                'text': {
                                    'body': 'Hello from WhatsApp'
                                },
                                'type': 'text'
                            }]
                        },
                        'field': 'messages'
                    }]
                }]
            }
        }
    }
    
    return result


class CustomAutoSchema(AutoSchema):
    """
    Custom AutoSchema class for enhanced API documentation.
    """
    
    def get_operation_id(self):
        """
        Generate operation IDs in a consistent format.
        """
        method = self.method.lower()
        
        if hasattr(self.view, 'get_operation_id'):
            return self.view.get_operation_id(method)
        
        # Extract app and model name from view
        view_name = self.view.__class__.__name__
        
        # Convert CamelCase to snake_case
        import re
        operation_id = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', view_name)
        operation_id = re.sub('([a-z0-9])([A-Z])', r'\1_\2', operation_id).lower()
        
        # Remove common suffixes
        operation_id = operation_id.replace('_view_set', '').replace('_view', '')
        
        return f"{method}_{operation_id}"
    
    def get_tags(self):
        """
        Determine tags for the operation based on the view.
        """
        if hasattr(self.view, 'get_tags'):
            return self.view.get_tags()
        
        # Extract tag from the view's app
        view_module = self.view.__module__
        if 'apps.news' in view_module:
            return ['News']
        elif 'apps.webhooks' in view_module:
            return ['Webhooks']
        elif 'apps.classification' in view_module:
            return ['Classification']
        elif 'apps.notifications' in view_module:
            return ['Notifications']
        else:
            return ['API']


# Custom serializer fields for better documentation
@extend_schema_field(serializers.CharField)
class UUIDField(serializers.UUIDField):
    """
    UUID field with better OpenAPI documentation.
    """
    class Meta:
        swagger_schema_fields = {
            'type': 'string',
            'format': 'uuid',
            'example': '12345678-1234-5678-9012-123456789012'
        }


@extend_schema_field(serializers.CharField)
class SlugField(serializers.SlugField):
    """
    Slug field with better OpenAPI documentation.
    """
    class Meta:
        swagger_schema_fields = {
            'type': 'string',
            'pattern': '^[-a-zA-Z0-9_]+$',
            'example': 'news-slug-example'
        }