"""Fail-closed route guards for dormant product phases."""

from functools import wraps

from django.conf import settings
from django.http import JsonResponse


def account_features_required(view_func):
    """Make a personal-data endpoint indistinguishable from a missing route."""

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not settings.ACCOUNT_FEATURES_ENABLED:
            return JsonResponse({'detail': 'Not found.'}, status=404)
        return view_func(request, *args, **kwargs)

    return wrapped
