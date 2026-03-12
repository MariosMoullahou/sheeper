from .helpers import get_active_farm, get_user_role


def active_farm(request):
    """Make the active farm and user role available in all templates."""
    if request.user.is_authenticated:
        return {
            'farm': get_active_farm(request),
            'user_role': get_user_role(request.user),
        }
    return {'farm': None, 'user_role': None}
