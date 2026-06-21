"""
Dashboard app — views.
Routes each user to the correct dashboard by role and supplies the data
each role needs, including the payment breakdown (total, deposit, amount
paid, balance owed) that all three roles can see.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from bookings.models import Booking
from rooms.models import Room
from concierge.models import ConciergeRequest
from accounts.decorators import role_required


@login_required
def home(request):
    """Send each user to the right dashboard based on their role."""
    # Read the role from the user's profile and redirect accordingly
    role = request.user.profile.role
    if role == 'manager':
        return redirect('dashboard:manager')
    elif role == 'receptionist':
        return redirect('dashboard:reception')
    return redirect('dashboard:guest')


@login_required
def guest_dashboard(request):
    """
    Guest dashboard. Shows the guest's bookings with the full payment
    breakdown so they always know what they have paid and still owe.
    """
    # Fetch the guest's active bookings (hide superseded edit history)
    bookings = Booking.objects.filter(
        guest=request.user
    ).exclude(status='superseded').select_related('room').prefetch_related('packages').order_by('-check_in')

    # Pending relocation offers needing the guest's decision, shown as a
    # banner so a disrupted booking is never missed.
    from relocations.models import RelocationOffer
    pending_offers = RelocationOffer.objects.filter(
        guest=request.user, status='pending'
    ).select_related('booking', 'original_room', 'new_room')

    context = {
        'bookings': bookings,
        'profile':  request.user.profile,
        'pending_offers': pending_offers,
    }
    return render(request, 'dashboard/guest.html', context)


@role_required('receptionist')
def reception_dashboard(request):
    """
    Reception dashboard. Shows today's arrivals and departures, the room
    board, pending concierge requests, and the balance owed on each
    booking so staff know what to collect.
    """
    today = timezone.now().date()

    # Today's arrivals: confirmed or due-in bookings checking in today
    arrivals = Booking.objects.filter(
        check_in=today, status__in=['confirmed', 'due-in']
    ).select_related('guest', 'room').prefetch_related('packages')

    # Today's departures: checked-in bookings checking out today
    departures = Booking.objects.filter(
        check_out=today, status='checked-in'
    ).select_related('guest', 'room')

    # All guests currently in-house (checked in), so staff can check anyone
    # out — including early departures before their booked check-out date.
    in_house = Booking.objects.filter(
        status='checked-in'
    ).select_related('guest', 'room').order_by('check_out')

    # All rooms for the live status board
    rooms = Room.objects.all().order_by('floor', 'room_number')

    # Requests that still need staff attention (pending or guest-countered)
    requests = ConciergeRequest.objects.filter(
        status__in=['pending', 'proposed']
    ).select_related('guest')

    # All relocation offers, so staff can follow up on guests who have not
    # yet decided. Pending ones with the guest's email are shown for contact.
    from relocations.models import RelocationOffer
    relocations = RelocationOffer.objects.select_related(
        'booking', 'guest', 'original_room', 'new_room'
    ).all()

    context = {
        'today':      today,
        'arrivals':   arrivals,
        'departures': departures,
        'in_house':   in_house,
        'rooms':      rooms,
        'requests':   requests,
        'relocations': relocations,
    }
    return render(request, 'dashboard/reception.html', context)


@role_required('manager')
def manager_dashboard(request):
    """
    Manager dashboard. Adds an operation-wide view including the aggregate
    total outstanding balance across all active bookings.
    """
    today = timezone.now().date()

    # All rooms, used for occupancy and housekeeping figures
    rooms = Room.objects.all()

    # All active bookings (exclude cancelled and superseded records)
    bookings = Booking.objects.exclude(
        status__in=['cancelled', 'superseded']
    ).select_related('guest', 'room').prefetch_related('packages')

    # Sum the balance owed across active bookings for the headline metric.
    # Checked-out bookings are settled at the desk (balance zeroed on
    # check-out) so they no longer contribute to what is outstanding.
    outstanding = bookings.exclude(status='checked-out').aggregate(
        total=Sum('balance_owed')
    )['total'] or 0

    # Sum what has actually been collected so far
    collected = bookings.aggregate(total=Sum('amount_paid'))['total'] or 0

    # All relocation offers for manager oversight of disruption handling
    from relocations.models import RelocationOffer
    relocations = RelocationOffer.objects.select_related(
        'booking', 'guest', 'original_room', 'new_room'
    ).all()

    context = {
        'today':           today,
        'rooms':           rooms,
        'bookings':        bookings,
        'occupied_count':  rooms.filter(status='occupied').count(),
        'vacant_count':    rooms.filter(status='vacant').count(),
        'total_rooms':     rooms.count(),
        'needs_cleaning':  rooms.filter(is_clean=False).count(),
        'outstanding':     outstanding,
        'collected':       collected,
        'relocations':     relocations,
    }
    return render(request, 'dashboard/manager.html', context)


@role_required('receptionist')
def check_in_booking(request, booking_id):
    """
    Staff action — check a guest in. Marks the booking checked-in and the
    room occupied. Used for arrivals, including walk-ins. POST only so it
    cannot be triggered by a crafted link.
    """
    from bookings.models import Booking
    booking = get_object_or_404(Booking, pk=booking_id)
    if request.method == 'POST':
        # Move the booking to checked-in and occupy its room
        booking.status = 'checked-in'
        booking.save()
        booking.room.status = 'occupied'
        booking.room.save()
        # Record who performed the check-in for the audit trail
        from maintenance.models import log_action
        log_action(request.user, 'check-in', f'BK{booking.pk} — {booking.guest.email} into {booking.room.room_number}', room=booking.room)
        messages.success(request, f'{booking.guest.get_full_name()} checked in to Room {booking.room.room_number}.')
    return redirect('dashboard:reception')


@role_required('receptionist')
def check_out_booking(request, booking_id):
    """
    Staff action — check a guest out. Marks the booking checked-out, frees
    the room and flags it as needing cleaning after departure.
    """
    from bookings.models import Booking
    booking = get_object_or_404(Booking, pk=booking_id)
    if request.method == 'POST':
        # Complete the stay: the guest settles any balance at the desk on
        # departure, so the booking is recorded as paid in full and shows
        # nothing outstanding on the staff totals afterwards.
        booking.amount_paid = booking.grand_total
        booking.balance_owed = 0
        booking.status = 'checked-out'
        booking.save()
        booking.room.status = 'vacant'
        booking.room.is_clean = False   # needs cleaning after departure
        booking.room.save()
        # Record who performed the check-out for the audit trail
        from maintenance.models import log_action
        log_action(request.user, 'check-out', f'BK{booking.pk} — {booking.room.room_number} vacated', room=booking.room)
        messages.success(request, f'Room {booking.room.room_number} checked out — flagged for cleaning.')
    return redirect('dashboard:reception')


@role_required('receptionist')
def toggle_clean(request, room_id):
    """
    Staff action — toggle a room's cleaned state after housekeeping
    inspection. Flips is_clean between true and false.
    """
    from rooms.models import Room
    room = get_object_or_404(Room, pk=room_id)
    if request.method == 'POST':
        # Flip the cleanliness flag and report the new state
        room.is_clean = not room.is_clean
        room.save()
        state = 'clean' if room.is_clean else 'needing cleaning'
        # Record who changed the cleanliness for the audit trail
        from maintenance.models import log_action
        log_action(request.user, 'clean' if room.is_clean else 'dirty', f'{room.room_number} marked {state}', room=room)
        messages.success(request, f'Room {room.room_number} marked as {state}.')
    return redirect('dashboard:reception')


@role_required('receptionist')
def toggle_maintenance(request, room_id):
    """
    Staff action — entry point from the room board's maintenance button.
    Sends staff to the maintenance form to choose a category and window
    when setting maintenance. The maintenance app owns the set/clear logic.
    """
    from rooms.models import Room
    room = get_object_or_404(Room, pk=room_id)
    if request.method == 'POST':
        # If the room already has active maintenance, send staff to the
        # board to clear or extend it; otherwise open the set-maintenance form.
        if room.maintenance_logs.filter(status='active').exists():
            return redirect('maintenance:board')
        return redirect('maintenance:set', room_id=room.pk)
    return redirect('dashboard:reception')
