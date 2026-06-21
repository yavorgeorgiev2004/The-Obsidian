"""
Relocation logic for the relocations app.

Pure functions that decide how to handle a booking whose room is going to
maintenance: how many free nights the stay earns, the cash value of that
compensation, and the best available room to move the guest into.
"""
from rooms.models import Room
from rooms.utils import available_rooms_for_dates

# Stays of this many nights or more count as a long stay for compensation.
LONG_STAY_THRESHOLD = 4

# Free nights granted by stay length, used to size the compensation.
LONG_STAY_FREE_NIGHTS = 2
SHORT_STAY_FREE_NIGHTS = 1


def free_nights_for(booking):
    """
    Return the number of free nights a booking earns when the guest is
    worse off after a forced move. Long stays earn more than short stays.
    """
    # Compare the booking length against the long-stay threshold
    if booking.nights() >= LONG_STAY_THRESHOLD:
        return LONG_STAY_FREE_NIGHTS
    return SHORT_STAY_FREE_NIGHTS


def bonus_credit(booking):
    """
    Return the cash value of the free-nights compensation: the room's
    nightly rate multiplied by the number of free nights earned.
    """
    # Value the free nights at the booking room's nightly price
    return booking.room.price_per_night * free_nights_for(booking)


def find_relocation(booking):
    """
    Work out the best way to move a booking off its current room for its
    dates. Returns a tuple of (resolution, new_room) where resolution is
    one of same / upgrade / downgrade / none and new_room is the chosen
    Room (or None when nothing is free).

    Preference order:
      1. a free room of the SAME type            -> 'same'
      2. a free room of a HIGHER-priced type     -> 'upgrade'
      3. a free room of a LOWER-priced type       -> 'downgrade'
      4. nothing free anywhere                     -> 'none'
    """
    current = booking.room

    # Collect every room free for the dates, excluding this booking itself
    free_rooms = [
        r for r in available_rooms_for_dates(booking.check_in, booking.check_out)
        if r.pk != current.pk
    ]

    # Step 1: prefer a same-type room, which needs no compensation
    same = [r for r in free_rooms if r.room_type == current.room_type]
    if same:
        return ('same', same[0])

    # Step 2: otherwise look for an upgrade (a more expensive room)
    upgrades = [r for r in free_rooms if r.price_per_night > current.price_per_night]
    if upgrades:
        # Pick the cheapest upgrade so the hotel absorbs the smallest cost
        upgrades.sort(key=lambda r: r.price_per_night)
        return ('upgrade', upgrades[0])

    # Step 3: otherwise a downgrade (a cheaper room), which earns compensation
    downgrades = [r for r in free_rooms if r.price_per_night < current.price_per_night]
    if downgrades:
        # Pick the dearest downgrade so the guest loses as little as possible
        downgrades.sort(key=lambda r: r.price_per_night, reverse=True)
        return ('downgrade', downgrades[0])

    # Step 4: nothing free at all for these dates
    return ('none', None)


def find_original_type_for_dates(booking, check_in, check_out):
    """
    When a guest reschedules, try to give them their ORIGINAL room type on
    the new dates first. Returns a free Room of the original type, or None.
    Used so a reschedule restores what they originally booked where possible.
    """
    # Look for a free room of the booking's original type on the new dates
    free = available_rooms_for_dates(check_in, check_out, booking.room.room_type)
    return free[0] if free else None
