"""
Integration tests for webhook system.
"""
import pytest
import json
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch

from apps.webhooks.models import WebhookLog
from apps.news.models import News


@pytest.mark.integration
class TestWebhookEndpoints:
    """Integration tests for webhook endpoints."""
    
    def test_webhook_source_crud(self, authenticated_client):
        """Test CRUD operations for webhook sources."""
        # Create
        url = reverse('webhooks:webhooksource-list')
        data = {
            'name': 'Test Webhook',
            'description': 'Test webhook source',
            'endpoint_url': 'https://test.example.com/webhook',
            'secret_key': 'test_secret',
            'expected_content_type': 'application/json',
            'requires_authentication': True,
            'rate_limit_per_minute': 100
        }
        
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        
        webhook_id = response.data['id']
        
        # Read
        url = reverse('webhooks:webhooksource-detail', kwargs={'pk': webhook_id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Test Webhook'
        
        # Update
        data = {'description': 'Updated description'}
        response = authenticated_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['description'] == 'Updated description'
        
        # Delete
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    def test_webhook_statistics(self, authenticated_client, webhook_source):
        """Test webhook source statistics endpoint."""
        url = reverse('webhooks:webhooksource-statistics', kwargs={'pk': webhook_source.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'source' in response.data
        assert 'recent_statistics' in response.data
    
    def test_webhook_test_endpoint(self, authenticated_client, webhook_source, mock_celery):
        """Test webhook source test endpoint."""
        url = reverse('webhooks:webhooksource-test', kwargs={'pk': webhook_source.id})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert 'webhook_log_id' in response.data


@pytest.mark.integration
@pytest.mark.django_db
class TestNewsWebhookReceiver:
    """Integration tests for news webhook receiver."""
    
    def test_receive_valid_webhook(self, api_client, webhook_source, sample_webhook_data, mock_celery):
        """Test receiving a valid webhook."""
        url = reverse('webhooks:news_webhook', kwargs={'source_name': webhook_source.name})
        
        response = api_client.post(
            url,
            data=json.dumps(sample_webhook_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert 'message' in response_data
        assert 'webhook_log_id' in response_data
        
        # Verify webhook log was created
        assert WebhookLog.objects.filter(source=webhook_source).exists()
    
    def test_receive_webhook_invalid_source(self, api_client, sample_webhook_data):
        """Test receiving webhook with invalid source."""
        url = reverse('webhooks:news_webhook', kwargs={'source_name': 'nonexistent'})
        
        response = api_client.post(
            url,
            data=json.dumps(sample_webhook_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_receive_webhook_invalid_json(self, api_client, webhook_source):
        """Test receiving webhook with invalid JSON."""
        url = reverse('webhooks:news_webhook', kwargs={'source_name': webhook_source.name})
        
        response = api_client.post(
            url,
            data='invalid json',
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_receive_webhook_missing_required_fields(self, api_client, webhook_source, mock_celery):
        """Test receiving webhook with missing required fields."""
        url = reverse('webhooks:news_webhook', kwargs={'source_name': webhook_source.name})
        
        invalid_data = {
            'title': 'Test News',
            # Missing content, source
        }
        
        response = api_client.post(
            url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        # Should accept the webhook but validation will fail in processing
        assert response.status_code == status.HTTP_200_OK
    
    @patch('apps.webhooks.views.verify_webhook_signature')
    def test_webhook_signature_verification(self, mock_verify, api_client, webhook_source, sample_webhook_data):
        """Test webhook signature verification."""
        webhook_source.requires_authentication = True
        webhook_source.save()
        
        # Test with valid signature
        mock_verify.return_value = True
        url = reverse('webhooks:news_webhook', kwargs={'source_name': webhook_source.name})
        
        response = api_client.post(
            url,
            data=json.dumps(sample_webhook_data),
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256='sha256=valid_signature'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Test with invalid signature
        mock_verify.return_value = False
        
        response = api_client.post(
            url,
            data=json.dumps(sample_webhook_data),
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256='sha256=invalid_signature'
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# WhatsApp webhook tests removed - external META Business API dependency not needed


@pytest.mark.integration
class TestWebhookDashboard:
    """Integration tests for webhook dashboard."""
    
    def test_webhook_dashboard(self, authenticated_client, webhook_source):
        """Test webhook dashboard endpoint."""
        url = reverse('webhooks:dashboard')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'overview' in response.data
        assert 'recent_logs' in response.data
        assert 'source_statistics' in response.data
        
        overview = response.data['overview']
        assert 'total_sources' in overview
        assert 'total_logs' in overview
        assert 'success_rate' in overview


@pytest.mark.integration
class TestWebhookProcessing:
    """Integration tests for webhook processing."""
    
    @patch('apps.webhooks.tasks.process_webhook_async.delay')
    def test_webhook_processing_task_triggered(self, mock_task, api_client, webhook_source, sample_webhook_data):
        """Test that webhook processing task is triggered."""
        url = reverse('webhooks:news_webhook', kwargs={'source_name': webhook_source.name})
        
        response = api_client.post(
            url,
            data=json.dumps(sample_webhook_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify task was called
        mock_task.assert_called_once()
    
    def test_webhook_log_creation(self, api_client, webhook_source, sample_webhook_data, mock_celery):
        """Test that webhook logs are created properly."""
        initial_log_count = WebhookLog.objects.count()
        
        url = reverse('webhooks:news_webhook', kwargs={'source_name': webhook_source.name})
        
        response = api_client.post(
            url,
            data=json.dumps(sample_webhook_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify log was created
        assert WebhookLog.objects.count() == initial_log_count + 1
        
        log = WebhookLog.objects.latest('created_at')
        assert log.source == webhook_source
        assert log.method == 'POST'
        assert log.status == 'processing'
        assert sample_webhook_data['title'] in log.body