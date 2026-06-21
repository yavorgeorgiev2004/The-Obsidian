"""
Bookings app — views.
Implements the dates-first booking flow (search dates, then choose from
a gallery of available room types), full booking editing with automatic
release of freed dates, and Stripe payments for both the initial deposit
and any later top-up owed after an edit.
"""
import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from .models import Booking, BookingPackage
from packages.models import Package
from rooms.models import Room
from rooms.utils import (
    room_types_available_for_dates,
    suggest_alternative,
    available_rooms_for_dates,
    is_room_available_for_dates,
)

# Configure Stripe using the secret key from the environment
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def search(request):
    """
    Step one of booking — the guest chooses dates and party size only.
    On submit we carry those values to the availability gallery.
    """
    # Provide sensible default dates for the picker: today and tomorrow
    today    = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    context = {
        'default_in':  today.isoformat(),
        'default_out': tomorrow.isoformat(),
    }
    return render(request, 'bookings/search.html', context)


@login_required
def gallery(request):
    """
    Step two — show a gallery of room types with live availability for
    the chosen dates. Fully booked types are shown but marked unavailable.
    """
    # Read the chosen dates and guest count from the query string
    check_in_str  = request.GET.get('check_in')
    check_out_str = request.GET.get('check_out')
    guests        = request.GET.get('guests', 1)

    # Without both dates we cannot show availability, so send them back
    if not check_in_str or not check_out_str:
        messages.error(request, 'Please choose your dates first.')
        return redirect('bookings:search')

    # Parse the date strings into date objects
    try:
        check_in  = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Those dates were not valid.')
        return redirect('bookings:search')

    # Guard against a check-out on or before the check-in
    if check_out <= check_in:
        messages.error(request, 'Check-out must be after check-in.')
        return redirect('bookings:search')

    # Build the per-type availability summary for these dates
    room_types = room_types_available_for_dates(check_in, check_out)

    context = {
        'room_types': room_types,
        'check_in':   check_in_str,
        'check_out':  check_out_str,
        'guests':     guests,
        'nights':     (check_out - check_in).days,
    }
    return render(request, 'bookings/gallery.html', context)


@login_required
def create_booking(request):
    """
    Step three — confirm a chosen room type for the chosen dates, add
    packages, then create the booking and move on to payment.
    """
    # Read the carried-over details from the query string or POST
    check_in_str  = request.GET.get('check_in')  or request.POST.get('check_in')
    check_out_str = request.GET.get('check_out') or request.POST.get('check_out')
    room_type     = request.GET.get('room_type') or request.POST.get('room_type')
    guests        = request.GET.get('guests')    or request.POST.get('guests', 1)

    # If the flow was reached without dates, restart at the search step
    if not check_in_str or not check_out_str or not room_type:
        return redirect('bookings:search')

    # Parse the dates
    check_in  = datetime.strptime(check_in_str, '%Y-%m-%d').date()
    check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()

    # Load active packages so the guest can add them to the stay
    packages = Package.objects.filter(is_active=True)

    if request.method == 'POST':
        # Find an actual free room of the chosen type for these dates
        free_rooms = available_rooms_for_dates(check_in, check_out, room_type)

        # If none remain free, the type sold out — send the guest back
        if not free_rooms:
            messages.error(request, 'That room type is no longer available for those dates.')
            return redirect(f'/bookings/gallery/?check_in={check_in_str}&check_out={check_out_str}&guests={guests}')

        # Take the first available room of the type
        room = free_rooms[0]

        # Create the booking as pending-payment. It holds the room during
        # checkout but is NOT confirmed until the deposit is actually paid,
        # so an abandoned checkout never leaves a confirmed unpaid booking.
        booking = Booking.objects.create(
            guest=request.user, room=room,
            check_in=check_in, check_out=check_out,
            guests_count=int(guests), status='pending-payment',
            special_requests=request.POST.get('special_requests', ''),
        )

        # Attach each selected package, storing its price at booking time
        for pkg_id in request.POST.getlist('packages'):
            try:
                pkg = Package.objects.get(package_id=pkg_id)
                BookingPackage.objects.create(
                    booking=booking, package=pkg, price_at_booking=pkg.price
                )
            except Package.DoesNotExist:
                continue

        # Recalculate totals now packages are attached, then save
        booking.calculate_totals()
        booking.save()

        # Move the guest to the deposit checkout
        return redirect('bookings:checkout', booking_id=booking.pk)

    # On GET, show the confirmation form with the carried details
    room_preview = Room.objects.filter(room_type=room_type).first()
    context = {
        'packages':     packages,
        'check_in':     check_in_str,
        'check_out':    check_out_str,
        'room_type':    room_type,
        'guests':       guests,
        'nights':       (check_out - check_in).days,
        'room_preview': room_preview,
    }
    return render(request, 'bookings/create.html', context)


@login_required
def my_bookings(request):
    """List all bookings belonging to the logged-in guest."""
    # Fetch the guest's bookings, excluding superseded edit history
    bookings = Booking.objects.filter(
        guest=request.user
    ).exclude(status='superseded').select_related('room').prefetch_related('packages').order_by('-check_in')
    return render(request, 'bookings/my_bookings.html', {'bookings': bookings})


@login_required
def edit_booking(request, booking_id):
    """
    Full edit of a booking — dates, guests, packages and room type.
    Changing the room type is treated as a new booking: the old one is
    superseded (freeing its dates) and a fresh record is created. Money
    already paid is carried across as a top-up or credited to the balance.
    """
    # Fetch the booking and confirm it belongs to the current guest
    booking = get_object_or_404(Booking, pk=booking_id, guest=request.user)

    # Load packages and room types for the edit form
    packages = Package.objects.filter(is_active=True)

    if request.method == 'POST':
        # Read the edited values from the form
        new_in    = datetime.strptime(request.POST.get('check_in'), '%Y-%m-%d').date()
        new_out   = datetime.strptime(request.POST.get('check_out'), '%Y-%m-%d').date()
        new_type  = request.POST.get('room_type')
        new_guests= int(request.POST.get('guests_count', 1))
        new_pkgs  = request.POST.getlist('packages')

        # Validate the date order before doing anything else
        if new_out <= new_in:
            messages.error(request, 'Check-out must be after check-in.')
            return redirect('bookings:edit', booking_id=booking.pk)

        # Decide whether the room type has changed
        type_changed = (new_type != booking.room.room_type)

        if type_changed:
            # A type change is handled as a brand new booking.
            # First find a free room of the new type for the new dates.
            free_rooms = available_rooms_for_dates(new_in, new_out, new_type)
            if not free_rooms:
                messages.error(request, 'That room type is not available for those dates.')
                return redirect('bookings:edit', booking_id=booking.pk)

            # Mark the old booking superseded, which frees its dates at once
            paid_so_far = booking.amount_paid
            booking.status = 'superseded'
            booking.save()

            # Create the replacement booking on the new room
            new_booking = Booking.objects.create(
                guest=request.user, room=free_rooms[0],
                check_in=new_in, check_out=new_out,
                guests_count=new_guests, status='confirmed',
                special_requests=booking.special_requests,
                amount_paid=paid_so_far,   # carry across what was already paid
            )

            # Attach the chosen packages to the new booking
            for pkg_id in new_pkgs:
                try:
                    pkg = Package.objects.get(package_id=pkg_id)
                    BookingPackage.objects.create(
                        booking=new_booking, package=pkg, price_at_booking=pkg.price
                    )
                except Package.DoesNotExist:
                    continue

            # Recalculate totals and the carried-over balance. Any amount
            # paid above the new total becomes account credit for the guest.
            overpayment = new_booking.calculate_totals()
            new_booking.save()
            if overpayment > 0:
                # Move the surplus to credit and reduce what was paid to the
                # new total, so the booking shows as paid in full, not over.
                request.user.profile.add_credit(overpayment)
                new_booking.amount_paid = new_booking.grand_total
                new_booking.balance_owed = 0
                new_booking.save()

            # Route to a top-up if more deposit is owed, else just confirm
            return _route_after_edit(new_booking)

        else:
            # Same room type — check the existing room is free for new dates,
            # ignoring this booking's own current dates during the check.
            if not is_room_available_for_dates(booking.room, new_in, new_out, exclude_booking_id=booking.pk):
                messages.error(request, 'Your room is not available for the new dates.')
                return redirect('bookings:edit', booking_id=booking.pk)

            # Apply the edited values to the existing record
            booking.check_in     = new_in
            booking.check_out    = new_out
            booking.guests_count = new_guests

            # Rebuild the package set: clear old links then add the new ones
            booking.bookingpackage_set.all().delete()
            for pkg_id in new_pkgs:
                try:
                    pkg = Package.objects.get(package_id=pkg_id)
                    BookingPackage.objects.create(
                        booking=booking, package=pkg, price_at_booking=pkg.price
                    )
                except Package.DoesNotExist:
                    continue

            # Recalculate totals against the new details. Any amount paid
            # above the new total becomes account credit for the guest.
            overpayment = booking.calculate_totals()
            booking.save()
            if overpayment > 0:
                # Move the surplus to credit and bring amount paid down to the
                # new total, so the booking reads as paid in full, not over.
                request.user.profile.add_credit(overpayment)
                booking.amount_paid = booking.grand_total
                booking.balance_owed = 0
                booking.save()

            # Route to a top-up if more is owed, else back to the dashboard
            return _route_after_edit(booking)

    # On GET, show the edit form pre-filled with the current values.
    # Build a list of room types with the price of one representative
    # room of each type, so the page can calculate totals live.
    type_prices = []
    seen = set()
    for room in Room.objects.all().order_by('price_per_night'):
        # Record each room type once, with its nightly price
        if room.room_type not in seen:
            seen.add(room.room_type)
            type_prices.append({
                'value': room.room_type,
                'label': room.get_room_type_display(),
                'price': room.price_per_night,
            })

    context = {
        'booking':      booking,
        'packages':     packages,
        'room_types':   type_prices,
        'current_pkgs': [bp.package.package_id for bp in booking.bookingpackage_set.all()],
    }
    return render(request, 'bookings/edit.html', context)


def _route_after_edit(booking):
    """
    Decide where to send the guest after an edit. If extra deposit is
    owed, go to the top-up payment; otherwise note any credit and return
    to the dashboard.
    """
    # Work out whether more deposit money is due after the edit
    top_up = booking.top_up_due()

    if top_up > 0:
        # More is owed, so send the guest to pay the difference
        return redirect('bookings:topup', booking_id=booking.pk)

    # Otherwise the guest may have a surplus already paid. Because the
    # balance owed is grand_total minus amount_paid, any surplus has
    # automatically reduced what they owe at the hotel — nothing to charge.
    return redirect('bookings:my_bookings')


@login_required
def check_availability(request):
    """
    JSON endpoint used by the edit page. Given a room type and dates,
    returns how many rooms of that type are free, so the guest can see
    availability live before saving. The booking being edited is excluded
    from the count so it does not block itself.
    """
    # Read the query parameters sent by the edit page's script
    room_type = request.GET.get('room_type')
    check_in_str = request.GET.get('check_in')
    check_out_str = request.GET.get('check_out')
    exclude_id = request.GET.get('exclude')

    # Without a type and both dates we cannot answer
    if not room_type or not check_in_str or not check_out_str:
        return JsonResponse({'error': 'missing parameters'}, status=400)

    # Parse the dates; bail out politely if they are invalid
    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'invalid dates'}, status=400)

    # Reject an impossible date order up front
    if check_out <= check_in:
        return JsonResponse({'available': 0, 'total': 0, 'status': 'invalid'})

    # Count rooms of this type that are free for the dates, excluding the
    # booking currently being edited so it does not count against itself.
    exclude_pk = int(exclude_id) if exclude_id and exclude_id.isdigit() else None
    rooms_of_type = Room.objects.filter(room_type=room_type)
    total = rooms_of_type.count()
    available = 0
    for room in rooms_of_type:
        if is_room_available_for_dates(room, check_in, check_out, exclude_booking_id=exclude_pk):
            available += 1

    # Decide a simple status label for the script to display
    if available == 0:
        status = 'full'
    elif available == 1:
        status = 'last-one'
    else:
        status = 'available'

    return JsonResponse({'available': available, 'total': total, 'status': status})


@login_required
def pay_deposit(request, booking_id):
    """
    Re-enter checkout for a booking still awaiting its deposit. Lets a
    guest who abandoned payment complete it later from their dashboard.
    """
    # Fetch the booking and confirm ownership, then send to checkout
    booking = get_object_or_404(Booking, pk=booking_id, guest=request.user)
    return redirect('bookings:checkout', booking_id=booking.pk)


@login_required
def checkout(request, booking_id):
    """
    Deposit checkout. Resolves the booking's payment state safely so a
    fully-paid booking never reaches Stripe:
      - already paid in full or deposit met -> straight to success, no charge
      - account credit can cover what is due -> a confirmation page applies
        the credit on submit (never on load), confirming the booking
      - otherwise -> a Stripe PaymentIntent is created for the remainder
    Credit may be applied against the full balance, not only the deposit.
    """
    # Fetch the booking and confirm ownership
    booking = get_object_or_404(Booking, pk=booking_id, guest=request.user)
    profile = request.user.profile

    # If nothing is due (deposit already met or booking fully paid), there is
    # nothing to charge. Make sure it is marked confirmed and go to success.
    if not booking.needs_payment():
        if booking.status == 'pending-payment':
            booking.status = 'confirmed'
            booking.save()
        messages.success(request, 'This booking is already secured — no payment is due.')
        return redirect('bookings:success', booking_id=booking.pk)

    # The deposit shortfall that must be settled now to secure the booking
    deposit_needed = booking.amount_due_now()

    # How much credit the guest could put towards what is owed. Credit can be
    # applied against the full remaining balance, but only the deposit is
    # required now, so the credit needed to secure the booking is the deposit.
    credit_available = profile.credit_balance

    # When credit can fully cover the deposit due, confirm via a page first
    # and apply the credit only on submit (never on GET).
    if credit_available >= deposit_needed:
        if request.method == 'POST':
            # The guest confirmed — apply credit toward the full balance owed
            # (up to the available credit), then confirm the booking.
            to_apply = min(credit_available, booking.balance_owed or booking.grand_total - booking.amount_paid)
            applied = profile.use_credit(to_apply)
            booking.apply_payment(applied)
            booking.status = 'confirmed'
            booking.save()
            messages.success(request, f'£{applied} of your account credit was applied. Your booking is confirmed.')
            return redirect('bookings:success', booking_id=booking.pk)

        # On GET, show the credit-confirmation page without spending anything.
        # Show how the credit clears the deposit so the guest is not confused.
        full_remaining = max(booking.grand_total - booking.amount_paid, 0)
        context = {
            'booking':        booking,
            'credit_balance': credit_available,
            'deposit_due':    deposit_needed,
            'full_remaining': full_remaining,
            'credit_covers_full': credit_available >= full_remaining,
        }
        return render(request, 'bookings/confirm_credit.html', context)

    # Otherwise, apply any partial credit, then charge the remainder by card.
    credit_applied = 0
    if credit_available > 0:
        credit_applied = profile.use_credit(deposit_needed)
        if credit_applied > 0:
            booking.apply_payment(credit_applied)

    # Recompute what is still owed on the deposit after any partial credit
    deposit_remaining = booking.amount_due_now()

    # Guard: if credit ended up covering the whole deposit, do not call Stripe
    if deposit_remaining <= 0:
        if booking.status == 'pending-payment':
            booking.status = 'confirmed'
            booking.save()
        messages.success(request, 'Your account credit covered the deposit — your booking is confirmed.')
        return redirect('bookings:success', booking_id=booking.pk)

    # The deposit in pence is what Stripe expects as an integer amount
    deposit_pence = int(round(deposit_remaining * 100))

    # Create a PaymentIntent for the deposit remainder
    intent = stripe.PaymentIntent.create(
        amount=deposit_pence, currency='gbp',
        metadata={'booking_id': booking.pk, 'kind': 'deposit'},
    )

    # Store the intent id so the webhook can match the payment later
    booking.stripe_payment_intent = intent.id
    booking.save()

    context = {
        'booking':           booking,
        'client_secret':     intent.client_secret,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'amount':            deposit_remaining,
        'credit_applied':    credit_applied,
        'pay_kind':          'Deposit',
        'success_url':       f'/bookings/{booking.pk}/success/',
    }
    return render(request, 'bookings/checkout.html', context)


@login_required
def topup(request, booking_id):
    """
    Top-up checkout shown after an edit that increased the deposit due.
    Charges only the difference between the deposit and what is paid.
    """
    # Fetch the booking and confirm ownership
    booking = get_object_or_404(Booking, pk=booking_id, guest=request.user)

    # The extra amount owed is the top-up figure, converted to pence
    topup_amount = booking.top_up_due()
    topup_pence  = int(topup_amount * 100)

    # Create a PaymentIntent for just the top-up difference
    intent = stripe.PaymentIntent.create(
        amount=topup_pence, currency='gbp',
        metadata={'booking_id': booking.pk, 'kind': 'topup'},
    )
    booking.stripe_payment_intent = intent.id
    booking.save()

    context = {
        'booking':           booking,
        'client_secret':     intent.client_secret,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'amount':            topup_amount,
        'pay_kind':          'Top-up',
        'success_url':       f'/bookings/{booking.pk}/topup-success/',
    }
    return render(request, 'bookings/checkout.html', context)


@login_required
def payment_success(request, booking_id):
    """Deposit success page. Records the deposit payment and confirms."""
    # Fetch the booking and confirm ownership
    booking = get_object_or_404(Booking, pk=booking_id, guest=request.user)

    # Record the deposit as paid against the booking
    booking.apply_payment(booking.deposit_amount() - booking.amount_paid)

    # Only now is the booking actually confirmed — payment has been made
    booking.status = 'confirmed'
    booking.save()

    # Award one loyalty point per pound of the grand total
    profile = request.user.profile
    profile.loyalty_points += int(booking.grand_total)
    profile.update_loyalty_tier()

    return render(request, 'bookings/success.html', {'booking': booking, 'kind': 'Deposit'})


@login_required
def topup_success(request, booking_id):
    """Top-up success page. Records the extra payment against the booking."""
    # Fetch the booking and confirm ownership
    booking = get_object_or_404(Booking, pk=booking_id, guest=request.user)

    # Apply the top-up so amount paid rises to the deposit due
    booking.apply_payment(booking.top_up_due())
    booking.save()

    return render(request, 'bookings/success.html', {'booking': booking, 'kind': 'Top-up'})


@login_required
def payment_failure(request, booking_id):
    """Failure feedback page shown when a payment did not complete."""
    booking = get_object_or_404(Booking, pk=booking_id, guest=request.user)
    return render(request, 'bookings/failure.html', {'booking': booking})


@login_required
def cancel_booking(request, booking_id):
    """
    Cancel a booking. Setting the status to cancelled frees its dates for
    other guests immediately, since availability is computed from active
    bookings only.
    """
    # Fetch the booking and confirm ownership
    booking = get_object_or_404(Booking, pk=booking_id, guest=request.user)

    if request.method == 'POST':
        # Mark cancelled — this alone releases the dates back to the pool
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, 'Your booking has been cancelled.')
        return redirect('bookings:my_bookings')

    return render(request, 'bookings/cancel.html', {'booking': booking})


@csrf_exempt
def stripe_webhook(request):
    """
    Stripe webhook. Verifies the event signature and records payments as
    a server-side safety net in case the browser redirect is interrupted.
    """
    payload    = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    # Verify the webhook signature against our configured secret
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return JsonResponse({'status': 'invalid'}, status=400)

    # Act on a successful payment by confirming the matching booking
    if event['type'] == 'payment_intent.succeeded':
        intent = event['data']['object']
        booking_id = intent.get('metadata', {}).get('booking_id')
        if booking_id:
            try:
                booking = Booking.objects.get(pk=booking_id)
                booking.status = 'confirmed'
                booking.save()
            except Booking.DoesNotExist:
                pass

    return JsonResponse({'status': 'success'})
