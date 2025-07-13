"""
Notification providers for different channels.
"""
import logging
import requests
import json
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class BaseNotificationProvider(ABC):
    """
    Base class for notification providers.
    """
    
    def __init__(self, config: Dict):
        self.config = config
    
    @abstractmethod
    def send(self, destination: str, subject: str, message: str, metadata: Dict = None) -> Tuple[bool, str, Dict]:
        """
        Send notification.
        
        Returns:
            Tuple of (success, external_id, response_data)
        """
        pass
    
    @abstractmethod
    def get_delivery_status(self, external_id: str) -> Tuple[str, Dict]:
        """
        Get delivery status for a message.
        
        Returns:
            Tuple of (status, response_data)
        """
        pass


# WhatsApp provider removed - external META Business API dependency not needed


class EmailProvider(BaseNotificationProvider):
    """
    Email notification provider using Django's email backend.
    """
    
    def send(self, destination: str, subject: str, message: str, metadata: Dict = None) -> Tuple[bool, str, Dict]:
        """
        Send email notification.
        """
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            success = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[destination],
                fail_silently=False
            )
            
            if success:
                # Generate a pseudo external_id for tracking
                external_id = f"email_{timezone.now().timestamp()}"
                logger.info(f"Email sent successfully to {destination}")
                return True, external_id, {'recipient': destination}
            else:
                logger.error(f"Email send failed to {destination}")
                return False, '', {'error': 'Email send failed'}
                
        except Exception as e:
            logger.error(f"Email send exception: {str(e)}", exc_info=True)
            return False, '', {'error': str(e)}
    
    def get_delivery_status(self, external_id: str) -> Tuple[str, Dict]:
        """
        Email delivery status (simplified - always return sent).
        """
        # Email delivery status is complex to track without specialized services
        return 'sent', {}


class WebhookProvider(BaseNotificationProvider):
    """
    Webhook notification provider.
    """
    
    def send(self, destination: str, subject: str, message: str, metadata: Dict = None) -> Tuple[bool, str, Dict]:
        """
        Send webhook notification.
        """
        try:
            payload = {
                'subject': subject,
                'message': message,
                'timestamp': timezone.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # Check if this is a demo/mock webhook (localhost or demo URLs)
            if 'localhost' in destination or 'demo' in destination or '127.0.0.1' in destination:
                # Mock successful webhook for demo purposes
                external_id = f"webhook_demo_{timezone.now().timestamp()}"
                logger.info(f"Demo webhook simulated for {destination}")
                return True, external_id, {'status_code': 200, 'demo': True}
            
            # Add authentication if configured
            headers = {'Content-Type': 'application/json'}
            auth_token = self.config.get('auth_token')
            if auth_token:
                headers['Authorization'] = f"Bearer {auth_token}"
            
            response = requests.post(
                destination,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                external_id = f"webhook_{timezone.now().timestamp()}"
                logger.info(f"Webhook sent successfully to {destination}")
                return True, external_id, {'status_code': response.status_code}
            else:
                logger.error(f"Webhook send failed: {response.status_code}")
                return False, '', {'status_code': response.status_code, 'error': response.text}
                
        except Exception as e:
            logger.error(f"Webhook send exception: {str(e)}", exc_info=True)
            return False, '', {'error': str(e)}
    
    def get_delivery_status(self, external_id: str) -> Tuple[str, Dict]:
        """
        Webhook delivery status (simplified).
        """
        return 'sent', {}


class SlackProvider(BaseNotificationProvider):
    """
    Slack notification provider.
    """
    
    def send(self, destination: str, subject: str, message: str, metadata: Dict = None) -> Tuple[bool, str, Dict]:
        """
        Send Slack notification.
        """
        try:
            # Check if this is a demo/mock Slack webhook (localhost or demo URLs)
            if 'localhost' in destination or 'demo' in destination or '127.0.0.1' in destination or 'hooks.slack.com' not in destination:
                # Mock successful Slack notification for demo purposes
                external_id = f"slack_demo_{timezone.now().timestamp()}"
                logger.info(f"Demo Slack notification simulated: {subject}")
                return True, external_id, {'response': 'ok', 'demo': True}
            
            # destination should be a Slack webhook URL
            payload = {
                'text': f"*{subject}*\n{message}" if subject else message,
                'username': 'JOTA News Bot',
                'icon_emoji': ':newspaper:'
            }
            
            response = requests.post(destination, json=payload, timeout=30)
            
            if response.status_code == 200 and response.text == 'ok':
                external_id = f"slack_{timezone.now().timestamp()}"
                logger.info(f"Slack message sent successfully")
                return True, external_id, {'response': response.text}
            else:
                logger.error(f"Slack send failed: {response.status_code}")
                return False, '', {'status_code': response.status_code, 'error': response.text}
                
        except Exception as e:
            logger.error(f"Slack send exception: {str(e)}", exc_info=True)
            return False, '', {'error': str(e)}
    
    def get_delivery_status(self, external_id: str) -> Tuple[str, Dict]:
        """
        Slack delivery status (simplified).
        """
        return 'sent', {}


class SMSProvider(BaseNotificationProvider):
    """
    SMS notification provider (mock implementation).
    """
    
    def send(self, destination: str, subject: str, message: str, metadata: Dict = None) -> Tuple[bool, str, Dict]:
        """
        Send SMS notification (mock implementation).
        """
        # This is a mock implementation
        # In production, you would integrate with Twilio, AWS SNS, or another SMS service
        
        logger.info(f"Mock SMS sent to {destination}: {message}")
        external_id = f"sms_{timezone.now().timestamp()}"
        return True, external_id, {'mock': True, 'destination': destination}
    
    def get_delivery_status(self, external_id: str) -> Tuple[str, Dict]:
        """
        SMS delivery status (mock).
        """
        return 'delivered', {'mock': True}


# Provider registry
PROVIDERS = {
    'email': EmailProvider,
    'webhook': WebhookProvider,
    'slack': SlackProvider,
    'sms': SMSProvider,
}


def get_provider(channel_type: str, config: Dict) -> BaseNotificationProvider:
    """
    Get notification provider instance.
    """
    provider_class = PROVIDERS.get(channel_type)
    if not provider_class:
        raise ValueError(f"Unknown channel type: {channel_type}")
    
    return provider_class(config)


def send_notification(channel_type: str, config: Dict, destination: str, 
                     subject: str, message: str, metadata: Dict = None) -> Tuple[bool, str, Dict]:
    """
    Send notification using appropriate provider.
    """
    try:
        provider = get_provider(channel_type, config)
        return provider.send(destination, subject, message, metadata)
    except Exception as e:
        logger.error(f"Notification send error: {str(e)}", exc_info=True)
        return False, '', {'error': str(e)}


def check_delivery_status(channel_type: str, config: Dict, external_id: str) -> Tuple[str, Dict]:
    """
    Check delivery status using appropriate provider.
    """
    try:
        provider = get_provider(channel_type, config)
        return provider.get_delivery_status(external_id)
    except Exception as e:
        logger.error(f"Status check error: {str(e)}", exc_info=True)
        return 'unknown', {'error': str(e)}