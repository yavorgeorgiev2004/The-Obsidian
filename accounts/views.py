"""Accounts app views — profile management."""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import UserProfile


@login_required
def profile(request):
    """Display and edit the current user's profile."""
    profile = request.user.profile
    return render(request, 'accounts/profile.html', {'profile': profile})
