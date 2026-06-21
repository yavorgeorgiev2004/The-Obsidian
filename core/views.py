"""
Core app views.
Homepage with live room availability. The homepage is viewable by everyone;
signed-in users still land on their dashboard at login (via the login
redirect setting) but can navigate to the homepage and back freely.
"""
from django.shortcuts import render
from rooms.utils import room_types_with_status


def home(request):
    """
    Homepage view, accessible to both anonymous and signed-in visitors.
    Shows the marketing homepage with live room-type availability. Signed-in
    users reach their dashboard from the navigation rather than being forced
    off this page.
    """
    # Build the live room-type availability summary for the rooms section
    room_types = room_types_with_status()

    return render(request, 'core/home.html', {'room_types': room_types})
