"""
SMS service integration.

Supports multiple SMS providers:
- Eskiz.uz (default)
- Playmobile
- Twilio

Switch providers by setting SMS_PROVIDER in .env
"""

import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(phone: str, message: str) -> bool:
    """
    Send SMS message to phone number.
    
    Supports multiple providers based on SMS_PROVIDER env var.
    In development, logs to console instead of sending.
    
    Args:
        phone: Phone number (format: +998XXXXXXXXX)
        message: SMS message text
    
    Returns:
        bool: True if sent successfully, False otherwise
    
    Example:
        send_sms('+998901234567', 'TradeLink tasdiqlash kodi: 123456')
    """
    
    if not phone or not message:
        logger.warning('SMS: Phone or message is empty')
        return False
    
    # In development, log and return success
    if settings.DEBUG:
        logger.info(f'[SMS DEV] To: {phone}, Message: {message}')
        return True
    
    # Get provider from settings (default: eskiz)
    provider = getattr(settings, 'SMS_PROVIDER', 'eskiz').lower()
    
    if provider == 'eskiz':
        return _send_via_eskiz(phone, message)
    elif provider == 'playmobile':
        return _send_via_playmobile(phone, message)
    elif provider == 'twilio':
        return _send_via_twilio(phone, message)
    else:
        logger.error(f'Unknown SMS provider: {provider}')
        return False


def _send_via_eskiz(phone: str, message: str) -> bool:
    """
    Send SMS via Eskiz.uz API (Uzbekistan).
    
    Requires:
    - SMS_API_KEY in .env
    - SMS_SENDER_NAME in .env
    
    API: https://api.eskiz.uz/api/message/send
    """
    try:
        import requests
        
        api_key = getattr(settings, 'SMS_API_KEY', None)
        sender_name = getattr(settings, 'SMS_SENDER_NAME', 'TradeLink')
        
        if not api_key:
            logger.error('SMS_API_KEY not configured for Eskiz')
            return False
        
        url = 'https://api.eskiz.uz/api/message/send'
        
        payload = {
            'mobile_phone': phone,
            'message': message,
            'from': sender_name,
        }
        
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info(f'SMS sent via Eskiz to {phone}')
            return True
        else:
            logger.error(f'Eskiz SMS failed: {response.status_code} - {response.text}')
            return False
            
    except Exception as e:
        logger.exception(f'Error sending SMS via Eskiz: {e}')
        return False


def _send_via_playmobile(phone: str, message: str) -> bool:
    """
    Send SMS via Playmobile API (Uzbekistan).
    
    Requires:
    - SMS_API_KEY in .env
    - SMS_SENDER_NAME in .env
    
    API: https://api.playmobile.kz/
    """
    try:
        import requests
        
        api_key = getattr(settings, 'SMS_API_KEY', None)
        sender_name = getattr(settings, 'SMS_SENDER_NAME', 'TradeLink')
        
        if not api_key:
            logger.error('SMS_API_KEY not configured for Playmobile')
            return False
        
        url = 'https://api.playmobile.kz/sms/sendPoint'
        
        payload = {
            'auth': {
                'login': api_key.split(':')[0] if ':' in api_key else api_key,
                'password': api_key.split(':')[1] if ':' in api_key else '',
            },
            'destination': phone,
            'type': 'flash',
            'text': message,
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f'SMS sent via Playmobile to {phone}')
            return True
        else:
            logger.error(f'Playmobile SMS failed: {response.status_code} - {response.text}')
            return False
            
    except Exception as e:
        logger.exception(f'Error sending SMS via Playmobile: {e}')
        return False


def _send_via_twilio(phone: str, message: str) -> bool:
    """
    Send SMS via Twilio API.
    
    Requires:
    - TWILIO_ACCOUNT_SID in .env
    - TWILIO_AUTH_TOKEN in .env
    - TWILIO_PHONE_NUMBER in .env
    
    API: https://www.twilio.com/docs/sms/api
    """
    try:
        from twilio.rest import Client
        
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        
        if not all([account_sid, auth_token, from_number]):
            logger.error('Twilio credentials not configured')
            return False
        
        client = Client(account_sid, auth_token)
        
        msg = client.messages.create(
            body=message,
            from_=from_number,
            to=phone
        )
        
        logger.info(f'SMS sent via Twilio to {phone} (SID: {msg.sid})')
        return True
        
    except Exception as e:
        logger.exception(f'Error sending SMS via Twilio: {e}')
        return False
