"""
Models for the complaints app.

A Complaint is raised by a guest and worked through by staff from open to
resolved. A manager may attach account credit as compensation when
resolving. The guest can always see the current status and any resolution.
"""
from django.db import models
from django.contrib.auth.models import User
from bookings.models import Booking


class Complaint(models.Model):
    """
    A guest complaint and its handling state. The status models a small
    workflow (open -> in-progress -> resolved) so both the guest and staff
    can see where it stands.
    """

    # The categories a complaint can fall under
    CATEGORY_CHOICES = [
        ('room',        'Room & Facilities'),
        ('service',     'Service'),
        ('cleanliness', 'Cleanliness'),
        ('noise',       'Noise'),
        ('billing',     'Billing'),
        ('other',       'Other'),
    ]

    # The handling states of a complaint
    STATUS_CHOICES = [
        ('open',        'Open'),
        ('in-progress', 'In Progress'),
        ('resolved',    'Resolved'),
    ]

    # Who raised it, the category, and the detail
    guest        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    category     = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    detail       = models.TextField()

    # An optional booking the complaint relates to
    booking      = models.ForeignKey(
        Booking, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='complaints'
    )

    # Current state and the staff handling/resolution
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    handled_by   = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='handled_complaints'
    )
    resolution   = models.TextField(blank=True)

    # Any account credit awarded as compensation on resolution
    credit_awarded = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Timestamps
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    resolved_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Complaint'
        verbose_name_plural = 'Complaints'

    def __str__(self):
        return f'{self.get_category_display()} — {self.guest.email} ({self.status})'
