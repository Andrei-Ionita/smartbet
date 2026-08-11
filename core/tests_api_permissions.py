"""
Every API view must state its permission policy explicitly.

This project sets no ``DEFAULT_PERMISSION_CLASSES``, so DRF's default is
``AllowAny``: a view that says nothing is public. That default is exactly how
three operational write endpoints came to be reachable by anyone —
``/api/update-fixture-results/``, ``/api/transparency/update-results/`` and
``/api/log-recommendations/`` — plus two dead ones removed on 2026-08-03,
``/api/fix-performance/`` and ``/api/mark-recommended/``.

"Public because nobody wrote it down" and "public by decision" must not look
the same. These tests fail when a new view is added without a declared policy,
so the decision has to be made and reviewed rather than inherited.

Deliberately NOT switching the global default to IsAuthenticated in this phase:
the inventory below includes genuinely public endpoints (registration, login,
published proof, transparency reads) and flipping the default would break them.
The inventory is the safer instrument.
"""
import inspect
import re

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import get_resolver
from rest_framework.test import APIClient

from core import api_views, auth_views, bankroll_views, internal_views, transparency_views

VIEW_MODULES = (
    api_views,
    auth_views,
    bankroll_views,
    internal_views,
    transparency_views,
)

# Plain Django views (not DRF). They are outside the DRF permission system, so
# their protection is documented here per view and asserted separately below.
#
#   read_only  — GET, no writes; safe to be public
#   hmac       — protected by core.services.ingest_auth (HMAC-SHA256)
#   public_write — intentionally public write, low value, no prediction impact
#   secret_header — guarded by a shared-secret header
NON_DRF_VIEWS = {
    'get_recommendations': 'read_only',
    'get_fixture_details': 'read_only',
    'get_fixture_context_timeline': 'read_only',
    'get_recommended_predictions_with_outcomes': 'read_only',
    'search_fixtures': 'read_only',
    'log_recommendations': 'hmac',
    'subscribe_email': 'public_write',
    'track_marketing_event': 'public_write',
    'marketing_webhook': 'secret_header',
}


def _decorated_functions(module):
    """(name, decorator source) for every decorated module-level function."""
    src = inspect.getsource(module)
    return [
        (m.group(2), m.group(1))
        for m in re.finditer(r'((?:^@[^\n]*\n)+)def (\w+)\(', src, re.M)
    ]


class ExplicitPermissionPolicyTests(TestCase):
    def test_every_drf_view_declares_permission_classes(self):
        undeclared = []
        for module in VIEW_MODULES:
            for name, decorators in _decorated_functions(module):
                if '@api_view' not in decorators:
                    continue
                if '@permission_classes' not in decorators:
                    undeclared.append(f'{module.__name__}.{name}')

        self.assertEqual(
            undeclared, [],
            'These DRF views inherit the implicit AllowAny default. Declare '
            '@permission_classes([...]) explicitly — public is a decision, not '
            'an accident:\n  ' + '\n  '.join(undeclared),
        )

    def test_every_non_drf_view_is_inventoried(self):
        """A new plain Django view must be classified here before it ships."""
        uninventoried = []
        for module in VIEW_MODULES:
            for name, decorators in _decorated_functions(module):
                if '@api_view' in decorators:
                    continue
                if 'require_http_methods' not in decorators and '@csrf_exempt' not in decorators:
                    continue
                if name not in NON_DRF_VIEWS:
                    uninventoried.append(f'{module.__name__}.{name}')

        self.assertEqual(
            uninventoried, [],
            'These non-DRF views are not in NON_DRF_VIEWS. Add each with its '
            'protection mechanism:\n  ' + '\n  '.join(uninventoried),
        )

    def test_no_view_uses_a_permission_class_that_does_not_exist(self):
        allowed = {'AllowAny', 'IsAuthenticated', 'IsAdminUser'}
        for module in VIEW_MODULES:
            for name, decorators in _decorated_functions(module):
                m = re.search(r'@permission_classes\(\[([^\]]*)\]\)', decorators)
                if not m:
                    continue
                for cls in (c.strip() for c in m.group(1).split(',') if c.strip()):
                    self.assertIn(
                        cls, allowed,
                        f'{module.__name__}.{name} uses an unrecognised permission '
                        f'class {cls!r}; document it in this test if intentional.',
                    )


class RemovedOperationalEndpointsTests(TestCase):
    """The write endpoints that the implicit default made public."""

    REMOVED = [
        '/api/update-fixture-results/',
        '/api/transparency/update-results/',
        '/api/fix-performance/',
        '/api/mark-recommended/',
    ]

    def test_all_are_gone(self):
        client = APIClient()
        for path in self.REMOVED:
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 404)
                self.assertEqual(client.post(path, {}, format='json').status_code, 404)

    def test_removed_view_callables_no_longer_exist(self):
        for name in ('update_fixture_results', 'fix_performance_metrics',
                     'mark_recommended_by_fixture_ids'):
            self.assertFalse(hasattr(api_views, name), name)
        self.assertFalse(hasattr(transparency_views, 'trigger_result_update'))


class PublicReadEndpointsStillWorkTests(TestCase):
    """Locking things down must not break the endpoints meant to be public."""

    PUBLIC_READS = [
        '/api/transparency/dashboard/',
        '/api/transparency/summary/',
        '/api/transparency/leagues/',
        '/api/transparency/recent/',
        '/api/transparency/quick-stats/',
    ]

    def test_anonymous_can_still_read_public_transparency(self):
        client = APIClient()
        for path in self.PUBLIC_READS:
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 200)


class OperationalWritesRejectAnonymousTests(TestCase):
    STAFF_ONLY = [
        ('/api/internal/scheduler-health/', 'get'),
        ('/api/proof/queue/', 'get'),
    ]

    def test_staff_endpoints_reject_anonymous(self):
        client = APIClient()
        for path, method in self.STAFF_ONLY:
            with self.subTest(path=path):
                resp = getattr(client, method)(path)
                self.assertIn(resp.status_code, (401, 403), f'{path} -> {resp.status_code}')

    def test_staff_endpoints_reject_authenticated_non_staff(self):
        user = User.objects.create_user('plain', 'p@example.com', 'x')
        client = APIClient()
        client.force_authenticate(user=user)
        for path, method in self.STAFF_ONLY:
            with self.subTest(path=path):
                resp = getattr(client, method)(path)
                self.assertEqual(resp.status_code, 403, f'{path} -> {resp.status_code}')

    def test_ingest_rejects_anonymous(self):
        resp = APIClient().post(
            '/api/log-recommendations/', {'recommendations': []}, format='json'
        )
        self.assertEqual(resp.status_code, 401)


class NoPublicGetPerformsWritesTests(TestCase):
    """A GET a browser can reach must never mutate operational state."""

    WRITE_MARKERS = (
        '.save(', '.create(', '.update(', '.delete(',
        'calculate_performance(', 'bulk_update(', 'bulk_create(',
    )

    def test_public_get_views_contain_no_write_calls(self):
        offenders = []
        for module in VIEW_MODULES:
            src = inspect.getsource(module)
            for name, decorators in _decorated_functions(module):
                is_get_only = (
                    "require_http_methods([\"GET\"])" in decorators
                    or "@api_view(['GET'])" in decorators
                )
                if not is_get_only:
                    continue
                # Staff-gated GETs are operational surfaces, not public ones.
                if 'IsAdminUser' in decorators or 'IsAuthenticated' in decorators:
                    continue
                body = src[src.index(f'def {name}('):]
                nxt = re.search(r'\n(?:@|def )', body[1:])
                body = body[: nxt.start()] if nxt else body
                for marker in self.WRITE_MARKERS:
                    if marker in body:
                        offenders.append(f'{module.__name__}.{name} -> {marker}')

        self.assertEqual(
            offenders, [],
            'These public GET views appear to perform writes:\n  '
            + '\n  '.join(offenders),
        )
