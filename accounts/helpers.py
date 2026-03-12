from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from rest_framework.response import Response
from rest_framework import status as http_status

from .models import Farm, ROLE_FARMER, ROLE_ANALYST, ROLE_MANAGER

SESSION_KEY = 'active_farm_id'


# ---------------------------------------------------------------------------
# Farm helpers
# ---------------------------------------------------------------------------

def get_active_farm(request):
    """Return the active Farm for the current session, or None."""
    farm_id = request.session.get(SESSION_KEY)
    if farm_id is None:
        return None

    role = get_user_role(request.user)

    # Managers can access any farm
    if role == ROLE_MANAGER or request.user.is_superuser:
        try:
            return Farm.objects.get(pk=farm_id)
        except Farm.DoesNotExist:
            return None

    # Farmers / analysts can only access their own farms
    try:
        return request.user.farms.get(pk=farm_id)
    except Farm.DoesNotExist:
        return None


def set_active_farm(request, farm):
    """Store the chosen farm in the session."""
    request.session[SESSION_KEY] = farm.pk


def get_user_farms(user):
    """Return the farms a user can access based on their role."""
    role = get_user_role(user)
    if role == ROLE_MANAGER or user.is_superuser:
        return Farm.objects.all()
    return user.farms.all()


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def get_user_role(user):
    """Return the role string for a user. Defaults to 'farmer'."""
    if user.is_superuser:
        return ROLE_MANAGER
    try:
        return user.profile.role
    except Exception:
        return ROLE_FARMER


# ---------------------------------------------------------------------------
# Decorators for page views
# ---------------------------------------------------------------------------

def role_required(*allowed_roles):
    """
    Decorator for page views. Returns 403 if the user's role is not in
    allowed_roles. Superusers always pass.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            role = get_user_role(request.user)
            if role not in allowed_roles:
                return HttpResponseForbidden("You don't have permission to access this page.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def api_role_required(*allowed_roles):
    """
    Decorator for DRF api_view functions. Returns 403 JSON response if the
    user's role is not in allowed_roles. Superusers always pass.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            role = get_user_role(request.user)
            if role not in allowed_roles:
                return Response(
                    {"detail": "You don't have permission to perform this action."},
                    status=http_status.HTTP_403_FORBIDDEN,
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
