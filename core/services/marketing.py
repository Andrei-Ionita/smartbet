import logging
import os
from urllib.parse import quote

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)
BREVO_API_BASE = 'https://api.brevo.com/v3'


class MarketingSyncError(Exception):
    pass


def marketing_sync_enabled():
    return os.getenv('MARKETING_SYNC_ENABLED', 'False') == 'True'


def _parse_int_list(raw_value):
    if not raw_value:
        return []
    values = []
    for item in str(raw_value).split(','):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(int(item))
        except ValueError:
            logger.warning('Ignoring invalid Brevo list id: %s', item)
    return values


def _brevo_headers():
    return {
        'accept': 'application/json',
        'api-key': os.getenv('BREVO_API_KEY', '').strip(),
        'content-type': 'application/json',
    }


def _brevo_enabled():
    return marketing_sync_enabled() and bool(os.getenv('BREVO_API_KEY', '').strip())


def _brevo_request(method, path, payload=None):
    response = requests.request(
        method,
        f'{BREVO_API_BASE}{path}',
        headers=_brevo_headers(),
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    if response.content:
        return response.json()
    return {}


def _brevo_contact_attributes(subscriber):
    mapping = {
        os.getenv('BREVO_ATTRIBUTE_SOURCE', '').strip(): subscriber.source,
        os.getenv('BREVO_ATTRIBUTE_LANDING_PAGE', '').strip(): subscriber.landing_page,
        os.getenv('BREVO_ATTRIBUTE_UTM_SOURCE', '').strip(): subscriber.utm_source,
        os.getenv('BREVO_ATTRIBUTE_UTM_MEDIUM', '').strip(): subscriber.utm_medium,
        os.getenv('BREVO_ATTRIBUTE_UTM_CAMPAIGN', '').strip(): subscriber.utm_campaign,
        os.getenv('BREVO_ATTRIBUTE_LANGUAGE', '').strip(): subscriber.language,
        os.getenv('BREVO_ATTRIBUTE_LEAGUE_INTEREST', '').strip(): subscriber.league_interest,
    }
    return {key: value for key, value in mapping.items() if key and value}


def _sync_brevo_contact(subscriber, action):
    default_list_ids = _parse_int_list(os.getenv('BREVO_DEFAULT_LIST_IDS', ''))
    paid_list_ids = _parse_int_list(os.getenv('BREVO_PAID_LIST_IDS', ''))
    contact_attributes = _brevo_contact_attributes(subscriber)

    if action in ('subscribe', 'reactivate'):
        payload = {
            'email': subscriber.email,
            'ext_id': str(subscriber.id),
            'emailBlacklisted': False,
            'updateEnabled': True,
        }
        if default_list_ids:
            payload['listIds'] = default_list_ids
        if contact_attributes:
            payload['attributes'] = contact_attributes
        _brevo_request('POST', '/contacts', payload)
        return

    if action == 'unsubscribe':
        payload = {'emailBlacklisted': True}
        if paid_list_ids:
            payload['unlinkListIds'] = paid_list_ids
        _brevo_request('PUT', f"/contacts/{quote(subscriber.email)}?identifierType=email_id", payload)
        return

    if action == 'paid_converted':
        payload = {
            'emailBlacklisted': False,
        }
        if paid_list_ids:
            payload['listIds'] = paid_list_ids
        if contact_attributes:
            payload['attributes'] = contact_attributes
        _brevo_request('PUT', f"/contacts/{quote(subscriber.email)}?identifierType=email_id", payload)


def _welcome_email_payload(subscriber, metadata=None):
    metadata = metadata or {}
    sender_email = os.getenv('BREVO_SENDER_EMAIL', '').strip()
    if not sender_email:
        return None

    sender_name = os.getenv('BREVO_SENDER_NAME', 'SmartBet').strip() or 'SmartBet'
    track_record_url = os.getenv('MARKETING_TRACK_RECORD_URL', 'https://betglitch.com/track-record').strip()
    pricing_url = os.getenv('MARKETING_PRICING_URL', 'https://betglitch.com/pricing').strip()

    payload = {
        'sender': {
            'name': sender_name,
            'email': sender_email,
        },
        'to': [
            {
                'email': subscriber.email,
            }
        ],
        'tags': [metadata.get('tag', 'welcome-flow')],
    }

    if os.getenv('BREVO_SANDBOX_MODE', 'False') == 'True':
        payload['headers'] = {'X-Sib-Sandbox': 'drop'}

    template_id = os.getenv('BREVO_WELCOME_TEMPLATE_ID', '').strip()
    if template_id:
        payload['templateId'] = int(template_id)
        payload['params'] = {
            'EMAIL': subscriber.email,
            'SOURCE': subscriber.source,
            'LEAGUE': subscriber.league_interest or 'Top Leagues',
            'TRACK_RECORD_URL': track_record_url,
            'PRICING_URL': pricing_url,
        }
        return payload

    payload['subject'] = 'Welcome to SmartBet weekly picks'
    payload['htmlContent'] = (
        '<html><body>'
        '<h1>Welcome to SmartBet</h1>'
        '<p>You are on the list for weekly AI-powered picks, public track-record updates, and premium launch notices.</p>'
        f'<p><strong>Track record:</strong> <a href="{track_record_url}">{track_record_url}</a></p>'
        f'<p><strong>Pricing roadmap:</strong> <a href="{pricing_url}">{pricing_url}</a></p>'
        '<p>We will keep the emails proof-led and low-noise.</p>'
        '</body></html>'
    )
    payload['textContent'] = (
        f'Welcome to SmartBet. Track record: {track_record_url}. '
        f'Pricing roadmap: {pricing_url}. '
        'You will receive weekly picks and premium launch updates.'
    )
    return payload


def _send_brevo_welcome_email(subscriber, metadata=None):
    if os.getenv('BREVO_WELCOME_EMAIL_ENABLED', 'False') != 'True':
        return

    payload = _welcome_email_payload(subscriber, metadata)
    if not payload:
        logger.warning('Brevo welcome email skipped because BREVO_SENDER_EMAIL is not configured')
        return

    _brevo_request('POST', '/smtp/email', payload)


def _sync_generic_webhook(subscriber, action, metadata=None):
    metadata = metadata or {}
    webhook_url = os.getenv('MARKETING_SYNC_WEBHOOK_URL', '').strip()
    if not webhook_url:
        return {'sent': False, 'reason': 'disabled'}

    payload = {
        'action': action,
        'subscriber': {
            'id': subscriber.id,
            'email': subscriber.email,
            'source': subscriber.source,
            'landing_page': subscriber.landing_page,
            'utm_source': subscriber.utm_source,
            'utm_medium': subscriber.utm_medium,
            'utm_campaign': subscriber.utm_campaign,
            'language': subscriber.language,
            'league_interest': subscriber.league_interest,
            'interests': subscriber.interests,
            'is_active': subscriber.is_active,
        },
        'metadata': metadata,
    }

    headers = {'Content-Type': 'application/json'}
    token = os.getenv('MARKETING_SYNC_TOKEN', '').strip()
    if token:
        headers['Authorization'] = f'Bearer {token}'

    response = requests.post(webhook_url, json=payload, headers=headers, timeout=5)
    response.raise_for_status()
    return {'sent': True}


def sync_marketing_profile(subscriber, action, metadata=None):
    metadata = metadata or {}

    if not marketing_sync_enabled():
        return {'sent': False, 'reason': 'disabled'}

    try:
        if _brevo_enabled():
            if action in ('subscribe', 'reactivate', 'unsubscribe', 'paid_converted'):
                _sync_brevo_contact(subscriber, action)
            if action in ('subscribe', 'reactivate'):
                _send_brevo_welcome_email(subscriber, metadata)
        else:
            _sync_generic_webhook(subscriber, action, metadata)
    except requests.RequestException as exc:
        logger.warning('Marketing sync failed for subscriber %s: %s', subscriber.email, exc)
        raise MarketingSyncError(str(exc)) from exc

    subscriber.last_synced_at = timezone.now()
    subscriber.email_platform_status = 'synced'
    subscriber.save(update_fields=['last_synced_at', 'email_platform_status'])
    return {'sent': True}
