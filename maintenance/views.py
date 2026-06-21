"""
Views for the maintenance app.

Staff set, extend and clear maintenance on rooms, and view the maintenance
board. Each action records the staff member responsible in the audit log.
Setting or extending maintenance over an existing booking hands that
booking to the relocations flow so the guest is looked after.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from accounts.decorators import role_required
from rooms.models import Room
from bookings.models import Booking
from .models import MaintenanceLog, log_action
from .utils import active_logs, escalation_counts


def _affected_bookings(room, start, end):
    """Return active bookings on a room that overlap a maintenance window."""
    # Bookings that are not cancelled/checked-out and overlap the window
    candidates = Booking.objects.filter(room=room).exclude(
        status__in=['cancelled', 'superseded', 'checked-out']
    )
    # Keep only those whose dates overlap the maintenance period
    return [b for b in candidates if b.check_in <= end and b.check_out > start]


@role_required('receptionist')
def set_maintenance(request, room_id):
    """
    Show and handle the form to place a room under maintenance. The expected
    ready date defaults from the chosen category and can be adjusted. If the
    window overlaps existing bookings, those are routed to the relocation
    flow rather than left on an unavailable room.
    """
    room = get_object_or_404(Room, pk=room_id)

    if request.method == 'POST':
        category = request.POST.get('category')
        notes = request.POST.get('notes', '')

        # Validate the category against the allowed choices
        valid = dict(MaintenanceLog.CATEGORY_CHOICES)
        if category not in valid:
            messages.error(request, 'Please choose a valid maintenance category.')
            return redirect('maintenance:set', room_id=room.pk)

        # Work out the window: today until the expected-ready date, which is
        # taken from the form if given, else the category default.
        start = timezone.now().date()
        ready_str = request.POST.get('expected_ready')
        if ready_str:
            try:
                expected_ready = datetime.strptime(ready_str, '%Y-%m-%d').date()
            except ValueError:
                expected_ready = MaintenanceLog.default_ready_date(category, start)
        else:
            expected_ready = MaintenanceLog.default_ready_date(category, start)

        # Reject an expected-ready date before the start
        if expected_ready < start:
            messages.error(request, 'The expected ready date cannot be in the past.')
            return redirect('maintenance:set', room_id=room.pk)

        # Create the maintenance log and mark the room for the board display
        MaintenanceLog.objects.create(
            room=room, category=category, notes=notes,
            started=start, expected_ready=expected_ready,
            status='active', created_by=request.user,
        )
        room.status = 'maintenance'
        room.save()

        # Record who set the maintenance for accountability
        log_action(request.user, 'maint-set', f'{room.room_number} — {valid[category]} until {expected_ready}', room=room)

        # Route any bookings caught in the window to the relocation flow
        affected = _affected_bookings(room, start, expected_ready)
        if affected:
            messages.success(request, f'Room {room.room_number} under maintenance. {len(affected)} booking(s) need relocating.')
            return redirect('relocations:confirm_maintenance', room_id=room.pk)

        messages.success(request, f'Room {room.room_number} placed under maintenance until {expected_ready}.')
        return redirect('maintenance:board')

    # On GET, show the form. Combine each category with its default days so
    # the template can render them without needing a custom filter.
    categories = [
        {'value': value, 'label': label, 'days': MaintenanceLog.DEFAULT_DAYS.get(value, 1)}
        for value, label in MaintenanceLog.CATEGORY_CHOICES
    ]
    context = {'room': room, 'categories': categories}
    return render(request, 'maintenance/set_maintenance.html', context)


@role_required('receptionist')
def extend_maintenance(request, log_id):
    """
    Push back a maintenance log's expected-ready date. If the new window
    now overlaps a booking, that booking is sent to the relocation flow.
    """
    log = get_object_or_404(MaintenanceLog, pk=log_id, status='active')

    if request.method == 'POST':
        # Read and validate the new expected-ready date
        ready_str = request.POST.get('expected_ready')
        try:
            new_ready = datetime.strptime(ready_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, 'Please choose a valid new date.')
            return redirect('maintenance:board')

        # The extension must move the date later than it is now
        if new_ready <= log.expected_ready:
            messages.error(request, 'The new date must be later than the current expected date.')
            return redirect('maintenance:board')

        # Apply the extension and record who did it
        log.expected_ready = new_ready
        log.save()
        log_action(request.user, 'maint-extend', f'{log.room.room_number} extended to {new_ready}', room=log.room)

        # An extension may now clash with a booking — route those if so
        affected = _affected_bookings(log.room, log.started, new_ready)
        if affected:
            messages.success(request, f'Maintenance extended. {len(affected)} booking(s) now need relocating.')
            return redirect('relocations:confirm_maintenance', room_id=log.room.pk)

        messages.success(request, f'Maintenance on Room {log.room.room_number} extended to {new_ready}.')
    return redirect('maintenance:board')


@role_required('receptionist')
def clear_maintenance(request, log_id):
    """
    Clear an active maintenance log, returning the room to service. This is
    the action that confirms the room is genuinely fixed and bookable again.
    """
    log = get_object_or_404(MaintenanceLog, pk=log_id, status='active')

    if request.method == 'POST':
        # Mark the log cleared, stamp who cleared it and when
        log.status = 'cleared'
        log.cleared_at = timezone.now()
        log.cleared_by = request.user
        log.save()

        # Return the room to service unless it has another active log
        if not log.room.maintenance_logs.filter(status='active').exists():
            log.room.status = 'vacant'
            log.room.save()

        log_action(request.user, 'maint-clear', f'{log.room.room_number} returned to service', room=log.room)
        messages.success(request, f'Room {log.room.room_number} returned to service.')
    return redirect('maintenance:board')


@role_required('receptionist')
def maintenance_board(request):
    """
    The maintenance tab. Lists active maintenance with each room's urgency
    level so staff can act before a window runs out, plus a count summary.
    """
    # Active logs and their escalation tallies for the summary badge
    logs = active_logs()
    context = {
        'logs':   logs,
        'counts': escalation_counts(),
    }
    return render(request, 'maintenance/board.html', context)


@role_required('manager')
def audit_log(request):
    """
    Manager-only view of the full staff action audit trail. Managers can
    review every logged action and who performed it; receptionists do not
    see this full history, only the last action on a room (shown elsewhere).
    """
    from .models import StaffActionLog
    # Most recent actions first, with staff and room preloaded
    logs = StaffActionLog.objects.select_related('staff', 'room')[:200]
    return render(request, 'maintenance/audit_log.html', {'logs': logs})


def last_action_for(room):
    """
    Return the most recent staff action on a room, or None. Used to show
    receptionists who last acted on a room without exposing the full log.
    """
    from .models import StaffActionLog
    # The single latest action record for this room
    return StaffActionLog.objects.filter(room=room).select_related('staff').first()
