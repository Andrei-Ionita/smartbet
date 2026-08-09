"""
Django settings for smartbet project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv
import sys
import urllib.parse
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Node opts into the Windows trust store through smartbet-frontend/.npmrc.
# Python's OpenSSL/certifi bundle cannot see local inspection roots (for
# example Avast Web/Mail Shield), so local HTTPS calls need the equivalent
# system-store bridge. Production Linux remains on its normal OpenSSL store.
if os.name == 'nt':
    import truststore

    truststore.inject_into_ssl()

# Quick-start development settings - unsuitable for production
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-^n-%7gq2z*i41-j(nxd93l$2y%p(fj@o%x0ugwk@-+r_75lsr4')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'django_filters',
    'core',
    'fixtures',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'smartbet.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'smartbet.wsgi.application'

# Database
if os.getenv('DATABASE_URL'):
    try:
        # CRITICAL FIX: Strip whitespace which breaks urlparse
        database_url = os.getenv('DATABASE_URL').strip()
        
        # Debug logging
        if not DEBUG:
            try:
                # Simple masking for logs
                safe_url = database_url
                if '@' in safe_url:
                    prefix, suffix = safe_url.split('@', 1)
                    if ':' in prefix:
                        scheme_user, _ = prefix.split(':', 1)
                        safe_url = f"{scheme_user}:****@{suffix}"
                print(f"DEBUG: Processing DATABASE_URL: {safe_url}", file=sys.stderr)
            except:
                print("DEBUG: Could not mask URL for logging", file=sys.stderr)

        # Handle Railway's custom scheme
        if 'railwaypostgresql://' in database_url:
            database_url = database_url.replace('railwaypostgresql://', 'postgresql://')
            if not DEBUG:
                print("DEBUG: Replaced railwaypostgresql:// scheme", file=sys.stderr)

        # Manual parsing using urllib
        url = urllib.parse.urlparse(database_url)
        
        # Verify parsing worked
        if not url.scheme:
            print(f"ERROR: urlparse failed to detect scheme. Raw URL start: '{database_url[:10]}...'", file=sys.stderr)
            # Attempt fallback if scheme is missing but it looks like a postgres url
            if 'postgres' in database_url and '://' not in database_url:
                 # Maybe it's just the connection string without scheme? Unlikely for Railway.
                 pass

        path = url.path[1:]
        
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': path,
                'USER': url.username,
                'PASSWORD': url.password,
                'HOST': url.hostname,
                'PORT': url.port,
                'CONN_MAX_AGE': 600,
            }
        }
        
        if not DEBUG:
            print(f"DEBUG: Database config created. ENGINE: postgresql, HOST: {url.hostname}, NAME: {path}, USER: {url.username}", file=sys.stderr)
            
    except Exception as e:
        print(f"ERROR: Failed to manually parse DATABASE_URL: {e}", file=sys.stderr)
        # Fallback to sqlite to prevent build crash
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Pricing-integrity cutoff: production vs tests ───────────────────────────
# PRODUCTION deliberately has NO default. When PRICING_INTEGRITY_CUTOFF is
# unset, core.services.public_universe falls back to a far-future sentinel, so
# every prediction classifies as legacy_unverified and nothing is published as
# verified. An unconfigured deployment under-claims rather than over-claims.
# That fail-closed property is a safety guarantee — do not add a default here.
#
# TESTS need the opposite: determinism. With the cutoff unset, ~54 claim and
# pricing tests fail for a reason unrelated to what they assert, which teaches
# people to ignore a red suite and hides real regressions. Tests therefore get
# ONE cutoff, defined here and nowhere else, never read from a developer's
# .env, so the same commit produces the same result on every machine and in CI.
#
# A test that specifically exercises the unconfigured case clears the variable
# and reloads public_universe — see core/tests_pricing_integrity_config.py.
TEST_PRICING_INTEGRITY_CUTOFF = '2026-07-30T08:32:00+00:00'

RUNNING_TESTS = (
    'test' in sys.argv
    or 'pytest' in sys.modules
    or bool(os.environ.get('PYTEST_CURRENT_TEST'))
)

if RUNNING_TESTS:
    # setdefault, not assignment: an explicit value from CI or from a developer
    # investigating a specific cutoff still wins.
    os.environ.setdefault('PRICING_INTEGRITY_CUTOFF', TEST_PRICING_INTEGRITY_CUTOFF)

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# SimpleJWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# CORS settings
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
else:
    CORS_ALLOW_ALL_ORIGINS = False
    # Prefer explicit multi-origin list (comma-separated); fall back to single FRONTEND_URL.
    _cors_env = os.getenv('CORS_ALLOWED_ORIGINS', '')
    if _cors_env:
        CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_env.split(',') if o.strip()]
    else:
        frontend_url = os.getenv('FRONTEND_URL', '')
        CORS_ALLOWED_ORIGINS = [frontend_url] if frontend_url else []

CORS_ALLOW_CREDENTIALS = True
CORS_PREFLIGHT_MAX_AGE = 86400

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'cache-control',
    'pragma',
    'expires',
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Security settings for production
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = False # Disabled to prevent health check redirect loops on Railway
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    # SECURE_HSTS_SECONDS = 31536000
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_HSTS_PRELOAD = True

    # CSRF Settings for Production
    CSRF_TRUSTED_ORIGINS = [
        'https://betglitch.com',
        'https://www.betglitch.com',
        'https://api.betglitch.com',
    ]
    if os.getenv('FRONTEND_URL'):
        CSRF_TRUSTED_ORIGINS.append(os.getenv('FRONTEND_URL'))
# ── Credential redaction on every log record ──────────────────────────────────
#
# On 2026-08-06 a test run printed the live SportMonks token to stdout. Nobody
# wrote a line that printed it: SportMonks authenticates by query parameter, and
# `requests` puts the fully resolved request URL into its exception message, so
# `logger.exception(...)` around any provider call writes the credential into
# the traceback.
#
# Call sites use core.services.redaction.redact_exception deliberately. This
# filter is the backstop for the ones that do not — including third-party
# libraries (urllib3, requests) that log their own request URLs, which we cannot
# edit. Attached to the root logger so nothing bypasses it.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'redact_secrets': {
            '()': 'core.services.redaction.RedactingFilter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['redact_secrets'],
            'formatter': 'standard',
        },
    },
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(message)s',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# ── Tests must never hold production credentials ──────────────────────────────
#
# The 2026-08-06 exposure happened DURING A TEST RUN: a provider call failed,
# `requests` put the resolved URL into the exception, and the print statement
# emitted the live token to stdout. Redaction now prevents the emission, but the
# deeper fix is that a test process has no business holding the real credential
# in the first place — it never calls the provider for real.
#
# Overriding here rather than in a separate settings module keeps it impossible
# to run the suite against production secrets by forgetting a flag.
if 'test' in sys.argv or os.environ.get('DJANGO_TEST_MODE') == '1':
    for _secret_var in (
        'SPORTMONKS_API_TOKEN',
        'SPORTMONKS_TOKEN',
        'INTERNAL_API_SECRET',
        'RECOMMENDATION_INGEST_SECRET',
        'MARKETING_WEBHOOK_SECRET',
        'POLAR_ACCESS_TOKEN',
        'POLAR_WEBHOOK_SECRET',
    ):
        if os.environ.get(_secret_var):
            os.environ[_secret_var] = f'FAKE_{_secret_var}_FOR_TESTS'
