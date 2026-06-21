"""
Concierge app — ConciergeRequest model.
Supports a negotiation flow: a guest submits a preferred time, staff may
propose an alternative, and the guest then confirms or counters. This
continues until both sides agree.
"""
from django.db import models
from django.contrib.auth.models import User


class ConciergeRequest(models.Model):
    """
    A bespoke guest request handled by staff. The status field models a
    small state machine so the guest always has the final say on timing.
    """

    # The categories of request a guest can choose from
    TYPE_CHOICES = [
        ('theatre',    'Theatre & Culture'),
        ('flowers',    'Flowers & Gifting'),
        ('shopping',   'Personal Shopping'),
        ('yacht',      'Yacht & Private Jet'),
        ('security',   'Privacy & Security'),
        ('pets',       'Pet Services'),
        ('photography','Photography & Film'),
        ('restaurant', 'Restaurant Reservation'),
        ('other',      'Something Else'),
    ]

    # The negotiation states:
    # pending  → guest submitted, staff not yet responded
    # proposed → staff proposed a different time, awaiting guest decision
    # confirmed→ both sides agree on the time
    # complete → the request has been fulfilled
    # cancelled→ called off
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('proposed',  'Time Proposed — Awaiting Guest'),
        ('confirmed', 'Confirmed'),
        ('complete',  'Complete'),
        ('cancelled', 'Cancelled'),
    ]

    # Who made the request and what type it is
    guest        = models.ForeignKey(User, on_delete=models.PROTECT, related_name='concierge_requests')
    request_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    detail       = models.TextField()

    # The guest's originally requested time
    requested_time = models.DateTimeField(null=True, blank=True)

    # A time the staff propose instead, if different from the request
    proposed_time  = models.DateTimeField(null=True, blank=True)

    # The final agreed time once confirmed by the guest
    confirmed_time = models.DateTimeField(null=True, blank=True)

    # Current negotiation status and any staff notes
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    staff_notes  = models.TextField(blank=True)

    # Which staff member is handling the request
    handled_by   = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='handled_requests'
    )

    # Timestamps
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Concierge Request'
        verbose_name_plural = 'Concierge Requests'

    def __str__(self):
        return f'{self.get_request_type_display()} — {self.guest.get_full_name()} ({self.status})'
