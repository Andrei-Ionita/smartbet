"""Transactional account email through the already-configured Brevo provider."""

import html
import os

import requests


BREVO_API_BASE = 'https://api.brevo.com/v3'


def configured():
    return bool(
        os.getenv('BREVO_API_KEY', '').strip()
        and os.getenv('BREVO_SENDER_EMAIL', '').strip()
    )


def send_password_reset(email, reset_url):
    """Send one password-reset message without logging the token or URL."""
    if not configured():
        raise RuntimeError('transactional email is not configured')

    sender_email = os.getenv('BREVO_SENDER_EMAIL', '').strip()
    sender_name = os.getenv('BREVO_SENDER_NAME', 'BetGlitch').strip() or 'BetGlitch'
    safe_url = html.escape(reset_url, quote=True)
    payload = {
        'sender': {'name': sender_name, 'email': sender_email},
        'to': [{'email': email}],
        'subject': 'Reset your BetGlitch password',
        'htmlContent': (
            '<html><body>'
            '<h1>Reset your BetGlitch password</h1>'
            '<p>Use the link below to choose a new password. The link becomes '
            'invalid after your password changes.</p>'
            f'<p><a href="{safe_url}">Choose a new password</a></p>'
            '<p>If you did not request this, you can ignore this email.</p>'
            '</body></html>'
        ),
        'textContent': (
            'Reset your BetGlitch password using this link: '
            f'{reset_url}\n\nIf you did not request this, ignore this email.'
        ),
        'tags': ['account-password-reset'],
    }
    if os.getenv('BREVO_SANDBOX_MODE', 'False') == 'True':
        payload['headers'] = {'X-Sib-Sandbox': 'drop'}

    response = requests.post(
        f'{BREVO_API_BASE}/smtp/email',
        headers={
            'accept': 'application/json',
            'api-key': os.getenv('BREVO_API_KEY', '').strip(),
            'content-type': 'application/json',
        },
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
