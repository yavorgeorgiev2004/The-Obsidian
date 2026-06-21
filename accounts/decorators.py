"""
Accounts app — custom access-control decorators.
These prevent non-authorised users from reaching staff or manager views,
satisfying the requirement that non-admin users cannot access the data
store directly without going through permission-checked code.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*allowed_roles):
    """
    Decorator that restricts a view to users whose profile role is in
    `allowed_roles`. Managers are always allowed through, as they have
    the highest level of access.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Anonymous users are sent to the login page first
            if not request.user.is_authenticated:
                return redirect('account_login')

            # Users without a profile cannot have a role, so block them
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'Your account has no profile assigned.')
                return redirect('core:home')

            role = request.user.profile.role

            # Managers bypass every role gate
            if role == 'manager':
                return view_func(request, *args, **kwargs)

            # Everyone else must match one of the allowed roles
            if role in allowed_roles:
                return view_func(request, *args, **kwargs)

            # Failing all checks, redirect to the user's own dashboard
            messages.error(request, 'You do not have permission to view that page.')
            return redirect('dashboard:home')
        return wrapper
    return decorator
