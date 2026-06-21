"""
Concierge app — views.
Implements the negotiation flow. A guest submits a request with a
preferred time; staff accept it or propose an alternative; the guest then
confirms the proposal or counters with another time. The guest always has
the final say before a request is confirmed.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime
from django.utils import timezone
from .models import ConciergeRequest
from .forms import ConciergeRequestForm
from accounts.decorators import role_required


@login_required
def create_request(request):
    """Create a new concierge request from the guest's submitted form."""
    if request.method == 'POST':
        # Bind the submitted data to the form for validation
        form = ConciergeRequestForm(request.POST)
        if form.is_valid():
            # Build the request, attach the guest and save it as pending
            req = form.save(commit=False)
            req.guest = request.user
            req.status = 'pending'
            req.save()
            messages.success(request, 'Your request has been received. Our concierge will respond shortly.')
            return redirect('concierge:my_requests')
    else:
        # On GET present a blank request form
        form = ConciergeRequestForm()
    return render(request, 'concierge/create.html', {'form': form})


@login_required
def my_requests(request):
    """List the guest's own requests so they can track and respond."""
    # Fetch only this guest's requests
    requests = ConciergeRequest.objects.filter(guest=request.user)
    return render(request, 'concierge/my_requests.html', {'requests': requests})


@login_required
def respond_to_proposal(request, request_id):
    """
    Guest side of the negotiation. When staff have proposed a time, the
    guest either confirms it or counters with a different preferred time.
    """
    # Fetch the request and confirm it belongs to this guest
    req = get_object_or_404(ConciergeRequest, pk=request_id, guest=request.user)

    if request.method == 'POST':
        # Read which action the guest chose
        action = request.POST.get('action')

        if action == 'confirm':
            # The guest accepts the staff-proposed time as final
            req.confirmed_time = req.proposed_time
            req.status = 'confirmed'
            req.save()
            messages.success(request, 'Your time has been confirmed. We look forward to it.')

        elif action == 'counter':
            # The guest proposes a different time, sending it back to staff
            counter_str = request.POST.get('counter_time')
            if counter_str:
                req.requested_time = timezone.make_aware(datetime.strptime(counter_str, '%Y-%m-%dT%H:%M'))
                req.proposed_time  = None
                req.status = 'pending'   # back to staff for another look
                req.save()
                messages.success(request, 'Your new preferred time has been sent to our concierge.')

        return redirect('concierge:my_requests')

    return render(request, 'concierge/respond.html', {'request_obj': req})


@role_required('receptionist')
def manage_request(request, request_id):
    """
    Staff side of the negotiation. Staff either accept the guest's time or
    propose an alternative, which puts the ball back in the guest's court.
    Protected by role_required so guests cannot reach it.
    """
    # Fetch the request being managed
    req = get_object_or_404(ConciergeRequest, pk=request_id)

    if request.method == 'POST':
        # Read which action the staff member took
        action = request.POST.get('action')

        # Always record who is handling it and any notes added
        req.handled_by  = request.user
        req.staff_notes = request.POST.get('staff_notes', req.staff_notes)

        if action == 'accept':
            # Staff accept the guest's requested time as the confirmed time
            req.confirmed_time = req.requested_time
            req.status = 'confirmed'
            messages.success(request, 'Request confirmed at the guest\'s requested time.')

        elif action == 'propose':
            # Staff propose an alternative time for the guest to confirm
            proposed_str = request.POST.get('proposed_time')
            if proposed_str:
                req.proposed_time = timezone.make_aware(datetime.strptime(proposed_str, '%Y-%m-%dT%H:%M'))
                req.status = 'proposed'
                messages.success(request, 'Alternative time proposed. Awaiting guest confirmation.')

        elif action == 'complete':
            # Mark a confirmed request as fulfilled
            req.status = 'complete'
            messages.success(request, 'Request marked complete.')

        req.save()
        return redirect('dashboard:reception')

    return render(request, 'concierge/manage.html', {'request_obj': req})
