"""
THE single commercial-mode switch (backend half).

Mirrors smartbet-frontend/app/lib/commercialMode.ts. Both sides read the SAME
effective configuration name so they cannot disagree about whether BetGlitch is
selling anything.

BetGlitch is presented as a free public beta while the company, billing setup
and payment-provider approval are being completed. No subscription code is
deleted — it is dormant, and re-enabling is one configuration change.

FAIL CLOSED: anything other than the exact string 'commercial' means payments
are OFF. A typo, an unset variable or a stray value all resolve to the beta.
"""
import os

COMMERCIAL = 'commercial'
PUBLIC_BETA = 'public_beta'


def commercial_mode():
    """Current mode. Read at call time so tests can override the environment."""
    # STRICT exact match, deliberately not case-insensitive: the frontend half
    # (app/lib/commercialMode.ts) compares exactly, and the two must agree about
    # whether BetGlitch is selling anything.
    raw = (os.environ.get('COMMERCIAL_MODE') or '').strip()
    return COMMERCIAL if raw == COMMERCIAL else PUBLIC_BETA


def payments_enabled():
    """True only when payments are deliberately enabled."""
    return commercial_mode() == COMMERCIAL


def is_public_beta():
    """True while BetGlitch is a free public beta."""
    return not payments_enabled()


# The API error every commerce endpoint returns while payments are off.
PAYMENTS_DISABLED_ERROR = {
    'code': 'payments_disabled',
    'detail': 'BetGlitch is currently operating as a free public beta.',
}
