"""
Rooms app — availability logic.
All availability is derived from the bookings table: a room is taken for
a date range only when an active booking overlaps it. This means editing
or cancelling a booking frees its dates automatically, with no manual
status updates required.
"""
from .models import Room


def is_room_available_for_dates(room, check_in, check_out, exclude_booking_id=None):
    """
    Decide whether one room is free across a requested date range by
    checking it against every active booking on that room, and against any
    active maintenance window on that room.
    """
    # Import here to avoid a circular import between rooms and bookings
    from bookings.models import Booking
    from django.utils import timezone
    from datetime import timedelta

    # Maintenance now blocks only the dates it actually covers, not the room
    # forever. Any active maintenance log whose window overlaps the request
    # makes the room unavailable for those dates; requests entirely after a
    # maintenance window are allowed, so the room frees up automatically.
    for log in room.maintenance_logs.filter(status='active'):
        # The same interval-overlap test used for bookings, applied to the
        # maintenance window (started .. expected_ready).
        if check_in <= log.expected_ready and check_out > log.started:
            return False

    # Gather active bookings on this room (ignore cancelled and superseded)
    active_bookings = Booking.objects.filter(room=room).exclude(
        status__in=['cancelled', 'superseded']
    )

    # Ignore abandoned checkouts: a booking still awaiting payment after a
    # short hold window no longer blocks the room, so a guest who closed the
    # checkout tab does not lock the room indefinitely.
    hold_cutoff = timezone.now() - timedelta(minutes=30)
    active_bookings = active_bookings.exclude(
        status='pending-payment', created_at__lt=hold_cutoff
    )

    # When editing a booking, ignore that booking's own existing dates
    if exclude_booking_id:
        active_bookings = active_bookings.exclude(pk=exclude_booking_id)

    # Check each booking for a date overlap with the requested range
    for booking in active_bookings:
        # Two ranges overlap when each begins before the other one ends
        if check_in < booking.check_out and check_out > booking.check_in:
            return False

    # Nothing overlapped, so the room is free for these dates
    return True


def room_types_available_for_dates(check_in, check_out):
    """
    Build a per-type availability summary for a date range, used by the
    booking gallery. For each room type it counts how many individual
    rooms are free and assigns a status of available, last-one or full.
    Returns a list of dicts ready for template rendering.
    """
    summary = {}

    # Group every room by its type and count how many are free for the dates
    for room in Room.objects.all().order_by('price_per_night'):
        key = room.room_type

        # Start a new entry the first time we see this type
        if key not in summary:
            summary[key] = {
                'type':          room.room_type,
                'type_display':  room.get_room_type_display(),
                'name':          room.name,
                'price':         room.price_per_night,
                'max_guests':    room.max_guests,
                'description':   room.description,
                'total':         0,
                'available':     0,
            }

        # Every room of this type counts toward the type total
        summary[key]['total'] += 1

        # Only free rooms count toward the available tally
        if is_room_available_for_dates(room, check_in, check_out):
            summary[key]['available'] += 1

    # Convert the grouped data into a list and attach a status label
    result = []
    for data in summary.values():
        available = data['available']

        # Decide the human-facing status from the available count
        if available == 0:
            data['status'] = 'full'           # no rooms of this type free
        elif available == 1:
            data['status'] = 'last-one'        # exactly one left — nudge the guest
        else:
            data['status'] = 'available'       # comfortably available
        result.append(data)

    return result


def suggest_alternative(room_types, requested_type):
    """
    When the guest's chosen type is full, suggest the nearest available
    type by price. Returns the suggested type dict, or None if every
    other type is also full.
    """
    # Find the price of the type the guest originally wanted
    requested = next((rt for rt in room_types if rt['type'] == requested_type), None)
    if not requested:
        return None
    requested_price = requested['price']

    # Keep only the types that still have availability
    available_types = [rt for rt in room_types if rt['status'] != 'full' and rt['type'] != requested_type]
    if not available_types:
        return None

    # Pick the available type whose price is closest to the requested one
    available_types.sort(key=lambda rt: abs(rt['price'] - requested_price))
    return available_types[0]


def room_types_with_status():
    """
    Simpler homepage summary. Shows each type's current availability based
    on live room status, so the marketing page can flag fully booked types.
    """
    summary = {}

    # Group rooms by type and count those currently vacant
    for room in Room.objects.all().order_by('price_per_night'):
        key = room.room_type
        if key not in summary:
            summary[key] = {
                'type': room.room_type, 'name': room.name,
                'type_display': room.get_room_type_display(),
                'price': room.price_per_night, 'total': 0, 'available': 0,
                'max_guests': room.max_guests, 'description': room.description,
            }
        summary[key]['total'] += 1
        if room.status == 'vacant':
            summary[key]['available'] += 1

    # Attach an availability flag and a status label for each type
    result = []
    for data in summary.values():
        data['is_available'] = data['available'] > 0
        if data['available'] == 0:
            data['status'] = 'full'
        elif data['available'] == 1:
            data['status'] = 'last-one'
        else:
            data['status'] = 'available'
        result.append(data)
    return result


def available_rooms_for_dates(check_in, check_out, room_type=None):
    """
    Return the actual Room objects free for a date range, optionally
    filtered to a single type. Used when assigning a specific room to a
    new booking.
    """
    rooms = Room.objects.all()

    # Narrow to one type if requested
    if room_type:
        rooms = rooms.filter(room_type=room_type)

    # Keep only rooms that pass the date-overlap check
    return [room for room in rooms if is_room_available_for_dates(room, check_in, check_out)]
