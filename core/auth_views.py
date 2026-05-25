"""
Authentication API views for SmartBet
Handles user registration, login, and token management
"""

import hmac
import os

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt

from .models import UserProfile


def _serialize_user(user: User) -> dict:
    """Single source of truth for what the frontend receives about a user.

    Always includes `tier` so AuthContext can read it without a separate fetch.
    The UserProfile is auto-created via a post_save signal; this is defensive
    in case a User predates the signal (legacy rows).
    """
    profile, _created = UserProfile.objects.get_or_create(user=user)
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'tier': profile.tier,
    }


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user.
    
    POST /api/auth/register/
    {
        "username": "user@email.com",
        "email": "user@email.com",
        "password": "securepassword",
        "first_name": "John",  # optional
        "last_name": "Doe"  # optional
    }
    """
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        # Validation
        if not username or not email or not password:
            return Response({
                'error': 'Username, email, and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            return Response({
                'error': 'Username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'Email already registered'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Password validation
        if len(password) < 8:
            return Response({
                'error': 'Password must be at least 8 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'User registered successfully',
            'user': _serialize_user(user),
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Registration failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login user and return JWT tokens.
    
    POST /api/auth/login/
    {
        "username": "user@email.com",
        "password": "securepassword"
    }
    """
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'error': 'Username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Support login by email: if input looks like an email, look up username
        login_input = username
        if '@' in login_input:
            try:
                email_user = User.objects.get(email=login_input)
                username = email_user.username
            except User.DoesNotExist:
                return Response({
                    'error': 'No account found with that email address'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'error': 'Account is disabled'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'user': _serialize_user(user),
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Login failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout user (blacklist refresh token).
    
    POST /api/auth/logout/
    {
        "refresh": "refresh_token_here"
    }
    """
    try:
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({
                'error': 'Refresh token required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        token = RefreshToken(refresh_token)
        token.blacklist()
        
        return Response({
            'success': True,
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': True,
            'message': 'Logout successful (token may have already expired)'
        }, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user(request):
    """
    Get current user information.
    
    GET /api/auth/user/
    Headers: Authorization: Bearer <access_token>
    """
    user = request.user

    return Response({
        'success': True,
        'user': {
            **_serialize_user(user),
            'date_joined': user.date_joined.isoformat(),
        }
    }, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Refresh access token using refresh token.
    
    POST /api/auth/token/refresh/
    {
        "refresh": "refresh_token_here"
    }
    """
    try:
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({
                'error': 'Refresh token required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        refresh = RefreshToken(refresh_token)
        
        return Response({
            'success': True,
            'access': str(refresh.access_token)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Invalid or expired refresh token'
        }, status=status.HTTP_401_UNAUTHORIZED)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def upgrade_tier(request):
    """
    Update a user's subscription tier. Called by the Polar webhook handler
    in smartbet-frontend after Polar fires subscription.{created,updated,
    canceled,revoked,...} events.

    POST /api/auth/upgrade-tier/
    Headers:
        X-Internal-Auth: <INTERNAL_API_SECRET>
    Body:
    {
        "email": "user@example.com",
        "tier": "pro" | "free",
        "subscription_id": "polar_sub_..."   (optional)
    }

    Returns 200 on success, 401 if the shared secret is wrong, 404 if the
    user doesn't exist, 400 for malformed input. Returns 200 (no-op) if the
    tier is already correct, to keep the webhook idempotent.
    """
    expected_secret = os.environ.get('INTERNAL_API_SECRET', '')
    provided_secret = request.META.get('HTTP_X_INTERNAL_AUTH', '')

    # If the secret isn't configured on the server, refuse rather than open
    # the endpoint up — the misconfiguration is more dangerous than the 401.
    if not expected_secret:
        return Response({
            'error': 'upgrade-tier endpoint is not configured (INTERNAL_API_SECRET unset)'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if not provided_secret or not hmac.compare_digest(provided_secret, expected_secret):
        return Response({'error': 'unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    email = (request.data.get('email') or '').strip().lower()
    tier = (request.data.get('tier') or '').strip().lower()
    subscription_id = request.data.get('subscription_id') or None

    if not email:
        return Response({'error': 'email is required'}, status=status.HTTP_400_BAD_REQUEST)
    if tier not in (UserProfile.TIER_FREE, UserProfile.TIER_PRO):
        return Response(
            {'error': f"tier must be one of: free, pro (got {tier!r})"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Email match is case-insensitive — User emails are case-sensitive in
        # the column but bookmakers / Polar normalize before sending.
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        # No matching user. We don't reveal the absence (return 404 is fine
        # since this is an internal-only endpoint).
        return Response(
            {'error': f"no user with email {email!r}"},
            status=status.HTTP_404_NOT_FOUND,
        )

    profile, _ = UserProfile.objects.get_or_create(user=user)
    previous_tier = profile.tier

    # Idempotent: if nothing changed, still return success so the webhook
    # doesn't retry. Update polar_subscription_id either way (re-binding to
    # a new subscription is a normal flow on plan changes).
    profile.set_tier(tier, polar_subscription_id=subscription_id)

    return Response({
        'success': True,
        'email': user.email,
        'previous_tier': previous_tier,
        'tier': profile.tier,
        'polar_subscription_id': profile.polar_subscription_id,
    }, status=status.HTTP_200_OK)
