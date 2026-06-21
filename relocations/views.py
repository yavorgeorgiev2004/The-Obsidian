"""
Views for the relocations app.

Two sides:
  - staff confirm placing a room under maintenance when it has bookings,
    and the system auto-resolves or flags each affected booking.
  - guests decide how to handle their own booking when it could not be
    auto-resolved (a downgrade or no room available).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from accounts.decorators import role_required
from bookings.models import Booking, BookingPackage
from rooms.models import Room
from .models import RelocationOffer
from .utils import find_relocation, free_nights_for, bonus_credit, find_original_type_for_dates


@role_required('receptionist')
def confirm_maintenance(request, room_id):
    """
    Staff-facing. Show the bookings that would be disrupted by placing a
    room under maintenance, with the auto-worked-out resolution for each.
    On POST, apply maintenance, auto-resolve same/upgrade moves, and create
    pending offers for downgrade / no-availability cases.
    """
    room = get_object_or_404(Room, pk=room_id)

    # Active future bookings on this room that maintenance would disrupt
    affected = Booking.objects.filter(room=room).exclude(
        status__in=['cancelled', 'superseded', 'checked-out']
    )

    # Pre-compute the resolution for each affected booking for display, and
    # flag which guests are currently in-house (checked in) so staff see it.
    previews = []
    for booking in affected:
        resolution, new_room = find_relocation(booking)
        previews.append({
            'booking': booking, 'resolution': resolution,
            'new_room': new_room, 'in_house': booking.status == 'checked-in',
            'bonus': bonus_credit(booking), 'free_nights': free_nights_for(booking),
        })

    if request.method == 'POST':
        for item in previews:
            booking = item['booking']
            resolution = item['resolution']
            new_room = item['new_room']

            # Staff decide per booking: 'move' to the suggested room, or
            # 'credit' to cancel for a refund of what was paid plus a bonus.
            action = request.POST.get(f'action_{booking.pk}', 'move')

            offer = RelocationOffer(
                booking=booking, guest=booking.guest,
                original_room=room, new_room=new_room,
                resolution=resolution,
            )

            if action == 'credit':
                # Staff chose to compensate rather than move: refund what was
                # paid as account credit plus a goodwill bonus, and release the
                # booking. Used for serious faults or at the guest's request.
                bonus = item['bonus']
                refund = booking.amount_paid + bonus
                booking.guest.profile.add_credit(refund)
                booking.status = 'cancelled'
                booking.save()
                offer.resolution = 'none'
                offer.bonus_credit = bonus
                offer.guest_choice = 'credit'
                offer.status = 'resolved'
                offer.resolved_at = timezone.now()
                offer.save()

            elif resolution in ('same', 'upgrade') and new_room is not None:
                # Move the booking to the suggested room immediately. The guest
                # is no worse off, so no compensation is attached.
                was_in_house = booking.status == 'checked-in'
                booking.room = new_room
                booking.calculate_totals()  # upgrade is free; keep paid amount
                booking.save()
                # When the guest is physically in the room, the new room
                # becomes occupied as they move straight into it.
                if was_in_house:
                    new_room.status = 'occupied'
                    new_room.save()
                offer.status = 'resolved'
                offer.resolved_at = timezone.now()
                offer.save()

            else:
                # Downgrade or nothing free: size the compensation and leave
                # the offer pending for the guest to choose how to proceed.
                offer.free_nights = free_nights_for(booking)
                offer.bonus_credit = bonus_credit(booking)
                offer.status = 'pending'
                offer.save()

        # Finally place the room under maintenance so it takes no new bookings
        room.status = 'maintenance'
        room.save()
        messages.success(request, f'Room {room.room_number} placed under maintenance. {len(previews)} booking(s) processed.')
        return redirect('dashboard:reception')

    # On GET, show the confirmation page listing the affected bookings
    context = {'room': room, 'previews': previews}
    return render(request, 'relocations/confirm_maintenance.html', context)


@login_required
def guest_decision(request, offer_id):
    """
    Guest-facing. For a pending downgrade or no-availability offer, let the
    owner choose how to proceed and apply their choice.

    Downgrade options:   keep-downgrade (+bonus) / credit / reschedule (+bonus)
    No-availability:     credit (+bonus) / reschedule (+bonus)
    """
    offer = get_object_or_404(RelocationOffer, pk=offer_id, guest=request.user)

    # Already-resolved offers have nothing to decide
    if offer.status != 'pending':
        messages.info(request, 'This relocation has already been resolved.')
        return redirect('dashboard:guest')

    booking = offer.booking
    profile = request.user.profile

    if request.method == 'POST':
        choice = request.POST.get('choice')

        if choice == 'keep-downgrade' and offer.resolution == 'downgrade':
            # Accept the cheaper room and take the free-nights value as credit.
            booking.room = offer.new_room
            booking.calculate_totals()
            booking.save()
            profile.add_credit(offer.bonus_credit)
            _resolve(offer, 'keep-downgrade')
            messages.success(request, f'Moved to {offer.new_room.name}. £{offer.bonus_credit} credit added for the inconvenience.')

        elif choice == 'credit':
            # Cancel the booking and return everything paid, plus the bonus,
            # as account credit usable on a future stay.
            refund = booking.amount_paid + offer.bonus_credit
            profile.add_credit(refund)
            booking.status = 'cancelled'
            booking.save()
            _resolve(offer, 'credit')
            messages.success(request, f'Booking cancelled. £{refund} credit added to your account (payment returned plus a bonus).')

        elif choice == 'reschedule':
            # Validate the new dates from the form
            try:
                new_in = datetime.strptime(request.POST.get('check_in'), '%Y-%m-%d').date()
                new_out = datetime.strptime(request.POST.get('check_out'), '%Y-%m-%d').date()
            except (ValueError, TypeError):
                messages.error(request, 'Please choose valid new dates.')
                return redirect('relocations:decide', offer_id=offer.pk)

            # Reject an impossible date order
            if new_out <= new_in:
                messages.error(request, 'Check-out must be after check-in.')
                return redirect('relocations:decide', offer_id=offer.pk)

            # Try to restore the guest's ORIGINAL room type on the new dates
            new_room = find_original_type_for_dates(booking, new_in, new_out)
            if not new_room:
                messages.error(request, 'Your original room type is not free on those dates. Try other dates or choose credit.')
                return redirect('relocations:decide', offer_id=offer.pk)

            # Move the booking to the new dates and room, recost, and credit
            # the bonus for the disruption.
            booking.room = new_room
            booking.check_in = new_in
            booking.check_out = new_out
            booking.calculate_totals()
            booking.save()
            profile.add_credit(offer.bonus_credit)
            _resolve(offer, 'reschedule')
            messages.success(request, f'Rebooked for {new_in} to {new_out}. £{offer.bonus_credit} credit added as a bonus.')

        else:
            messages.error(request, 'Please choose an option.')
            return redirect('relocations:decide', offer_id=offer.pk)

        return redirect('dashboard:guest')

    # On GET, show the decision page with the options for this offer type
    context = {'offer': offer, 'booking': booking}
    return render(request, 'relocations/guest_decision.html', context)


def _resolve(offer, choice):
    """Mark an offer resolved and record which option the guest picked."""
    # Stamp the offer as resolved with the chosen option and time
    offer.guest_choice = choice
    offer.status = 'resolved'
    offer.resolved_at = timezone.now()
    offer.save()


@role_required('receptionist')
def staff_record_decision(request, offer_id):
    """
    Staff-facing. Record, on the guest's behalf, the decision a guest gave
    by phone or in person. Applies the same outcomes as the guest's own
    decision page so the money logic is not duplicated. Never auto-cancels:
    this only runs when a staff member actively submits a choice.
    """
    offer = get_object_or_404(RelocationOffer, pk=offer_id)

    # Nothing to do if the offer is already resolved
    if offer.status != 'pending':
        messages.info(request, 'This relocation has already been resolved.')
        return redirect('dashboard:reception')

    booking = offer.booking
    profile = offer.guest.profile

    if request.method == 'POST':
        choice = request.POST.get('choice')

        if choice == 'keep-downgrade' and offer.resolution == 'downgrade':
            # Move the booking to the cheaper room and credit the bonus
            booking.room = offer.new_room
            booking.calculate_totals()
            booking.save()
            profile.add_credit(offer.bonus_credit)
            _resolve(offer, 'keep-downgrade')
            messages.success(request, f'Recorded: BK{booking.pk} moved to {offer.new_room.name}, £{offer.bonus_credit} credit applied.')

        elif choice == 'credit':
            # Cancel and convert payment plus bonus to account credit
            refund = booking.amount_paid + offer.bonus_credit
            profile.add_credit(refund)
            booking.status = 'cancelled'
            booking.save()
            _resolve(offer, 'credit')
            messages.success(request, f'Recorded: BK{booking.pk} cancelled, £{refund} credit applied (payment plus bonus).')

        elif choice == 'reschedule':
            # Validate the new dates supplied by staff
            try:
                new_in = datetime.strptime(request.POST.get('check_in'), '%Y-%m-%d').date()
                new_out = datetime.strptime(request.POST.get('check_out'), '%Y-%m-%d').date()
            except (ValueError, TypeError):
                messages.error(request, 'Please enter valid new dates.')
                return redirect('dashboard:reception')

            # Reject an impossible date order
            if new_out <= new_in:
                messages.error(request, 'Check-out must be after check-in.')
                return redirect('dashboard:reception')

            # Try to restore the original room type on the new dates
            new_room = find_original_type_for_dates(booking, new_in, new_out)
            if not new_room:
                messages.error(request, 'Original room type not free on those dates. Try other dates or record credit.')
                return redirect('dashboard:reception')

            # Apply the new dates and room, recost, and credit the bonus
            booking.room = new_room
            booking.check_in = new_in
            booking.check_out = new_out
            booking.calculate_totals()
            booking.save()
            profile.add_credit(offer.bonus_credit)
            _resolve(offer, 'reschedule')
            messages.success(request, f'Recorded: BK{booking.pk} rebooked for {new_in} to {new_out}, £{offer.bonus_credit} bonus credit applied.')

        else:
            messages.error(request, 'Please choose an option to record.')
            return redirect('dashboard:reception')

        # Record which staff member recorded this guest decision
        from maintenance.models import log_action
        log_action(request.user, 'relocation', f'BK{booking.pk} — recorded {choice} for {offer.guest.email}', room=offer.original_room)

        return redirect('dashboard:reception')

    # On GET, show the staff record-decision form for this offer
    context = {'offer': offer, 'booking': booking}
    return render(request, 'relocations/staff_record.html', context)
