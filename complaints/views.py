"""
Views for the complaints app.

Guests raise complaints and track their status. Staff (reception and
managers) see all complaints and move them through the workflow; only
managers may attach account credit as compensation when resolving.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from accounts.decorators import role_required
from .models import Complaint
from .forms import ComplaintForm


@login_required
def create_complaint(request):
    """Let a guest raise a complaint tied to their account."""
    if request.method == 'POST':
        # Validate the submitted complaint, scoped to this guest's bookings
        form = ComplaintForm(request.POST, user=request.user)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.guest = request.user
            complaint.status = 'open'
            complaint.save()
            messages.success(request, 'Your complaint has been logged. Our team will look into it.')
            return redirect('complaints:my_complaints')
    else:
        # On GET present a blank complaint form
        form = ComplaintForm(user=request.user)
    return render(request, 'complaints/create.html', {'form': form})


@login_required
def my_complaints(request):
    """Show the guest their own complaints with status and resolution."""
    # Only this guest's complaints, newest first
    complaints = Complaint.objects.filter(guest=request.user).select_related('booking')
    return render(request, 'complaints/my_complaints.html', {'complaints': complaints})


@role_required('receptionist')
def complaint_queue(request):
    """Staff view of all complaints needing attention and their state."""
    # Every complaint, with guest and booking preloaded for display
    complaints = Complaint.objects.select_related('guest', 'booking', 'handled_by')
    is_manager = request.user.profile.role == 'manager'
    return render(request, 'complaints/queue.html', {
        'complaints': complaints, 'is_manager': is_manager,
    })


@role_required('receptionist')
def manage_complaint(request, complaint_id):
    """
    Staff handle a complaint: move it to in-progress or resolved, record a
    resolution note, and (managers only) attach account credit as
    compensation. The credit is added to the guest's balance on resolution.
    """
    complaint = get_object_or_404(Complaint, pk=complaint_id)
    is_manager = request.user.profile.role == 'manager'

    if request.method == 'POST':
        action = request.POST.get('action')

        # Always record which staff member is handling it
        complaint.handled_by = request.user

        if action == 'progress':
            # Move an open complaint into active handling
            complaint.status = 'in-progress'
            messages.success(request, 'Complaint marked in progress.')

        elif action == 'resolve':
            # Record the resolution text and close the complaint
            complaint.status = 'resolved'
            complaint.resolution = request.POST.get('resolution', '')
            complaint.resolved_at = timezone.now()

            # Only a manager may attach account credit as compensation
            if is_manager:
                credit_str = request.POST.get('credit_awarded', '').strip()
                if credit_str:
                    try:
                        amount = Decimal(credit_str)
                    except (InvalidOperation, ValueError):
                        amount = Decimal('0')
                    # Apply a positive award to the guest's credit balance
                    if amount > 0:
                        complaint.credit_awarded = amount
                        complaint.guest.profile.add_credit(amount)
            messages.success(request, 'Complaint resolved.')

        complaint.save()
        return redirect('complaints:queue')

    return render(request, 'complaints/manage.html', {
        'complaint': complaint, 'is_manager': is_manager,
    })
