"""
Rooms app — views.
Provides the public room listing and room detail pages. Supports
date-based availability filtering so guests only see rooms that are
genuinely free for their chosen dates.
"""
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import Room
from .utils import available_rooms_for_dates, room_types_available_for_dates, room_types_with_status


def room_list(request):
    """
    Display rooms grouped by type. When the guest supplies check-in and
    check-out dates, each type shows how many rooms are free for those
    dates; otherwise each type shows its current availability.
    """
    # Read optional date filters from the URL query string
    check_in_str  = request.GET.get('check_in')
    check_out_str = request.GET.get('check_out')

    filtered = False
    room_types = []
    date_error = None

    # When both dates are given, group by type with date-accurate availability
    if check_in_str and check_out_str:
        try:
            check_in  = timezone.datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = timezone.datetime.strptime(check_out_str, '%Y-%m-%d').date()

            # Validate the range: check-out must be after check-in. Rather than
            # silently reloading, report the problem so the guest can correct it.
            if check_out <= check_in:
                date_error = 'Your check-out date must be after your check-in date.'
                room_types = room_types_with_status()
            else:
                room_types = room_types_available_for_dates(check_in, check_out)
                filtered = True
        except ValueError:
            # Malformed dates fall back to the current-status summary
            room_types = room_types_with_status()
    else:
        # No dates supplied — show each type's current availability
        room_types = room_types_with_status()

    # Provide sensible default dates for the picker (today and tomorrow)
    today    = timezone.now().date()
    tomorrow = today + timedelta(days=1)

    context = {
        'room_types':   room_types,
        'filtered':     filtered,
        'date_error':   date_error,
        'default_in':   today.isoformat(),
        'default_out':  tomorrow.isoformat(),
        # Logged-in guests see the portal shell (with their sidebar);
        # anonymous visitors see the public marketing shell.
        'base_template': 'portal_base.html' if request.user.is_authenticated else 'base.html',
    }
    return render(request, 'rooms/list.html', context)


def room_detail(request, room_id):
    """Display a single room's full detail."""
    # Fetch the room or raise a 404 if it does not exist
    room = get_object_or_404(Room, pk=room_id)
    context = {
        'room': room,
        'base_template': 'portal_base.html' if request.user.is_authenticated else 'base.html',
    }
    return render(request, 'rooms/detail.html', context)
