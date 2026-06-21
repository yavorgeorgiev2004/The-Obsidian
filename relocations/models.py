"""
Models for the relocations app.

Holds the record created when a booking must be moved because its room is
placed under maintenance. One RelocationOffer is created per affected
booking and tracks how the disruption was resolved and any compensation.
"""
from django.db import models
from django.contrib.auth.models import User
from bookings.models import Booking
from rooms.models import Room


class RelocationOffer(models.Model):
    """
    Records a single booking's relocation after its room went to
    maintenance. Stores the resolution category, the room moved from and
    to, any compensation credit, and whether the guest has acted on it.
    """

    # Resolution categories, set when the relocation is first worked out.
    # same     = moved to another room of the same type, no compensation
    # upgrade  = moved to a higher type free of charge, no compensation
    # downgrade= only a lesser room was free, compensation applies
    # none     = nothing free for the dates, booking must be cancelled
    RESOLUTION_CHOICES = [
        ('same',      'Same Type — No Compensation'),
        ('upgrade',   'Free Upgrade — No Compensation'),
        ('downgrade', 'Downgrade — Compensation Due'),
        ('none',      'No Room Available — Cancel or Reschedule'),
    ]

    # Lifecycle of the offer. Offers needing a guest decision stay pending
    # until the guest chooses; auto-resolved moves are marked resolved.
    STATUS_CHOICES = [
        ('pending',  'Awaiting Guest Decision'),
        ('resolved', 'Resolved'),
    ]

    # The booking being relocated and who owns it.
    booking      = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='relocations')
    guest        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='relocation_offers')

    # The room moved out of, and the room moved into (null until assigned).
    original_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, related_name='relocations_from')
    new_room      = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='relocations_to')

    # How the disruption was categorised, and current status.
    resolution   = models.CharField(max_length=20, choices=RESOLUTION_CHOICES)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Compensation: the free-nights value offered as credit when the guest
    # is worse off (downgrade or cancellation). Zero for same/upgrade moves.
    bonus_credit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # The number of free nights the stay length earned (0, 1 or 2).
    free_nights  = models.PositiveSmallIntegerField(default=0)

    # What the guest chose, once they decide (for downgrade/none cases).
    guest_choice = models.CharField(max_length=20, blank=True)

    created_at   = models.DateTimeField(auto_now_add=True)
    resolved_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Relocation Offer'
        verbose_name_plural = 'Relocation Offers'

    def __str__(self):
        return f'Relocation for BK{self.booking_id} ({self.resolution})'

    def needs_guest_decision(self):
        """True when the offer is waiting on the guest to choose an option."""
        # Only downgrade and no-availability offers require a guest choice
        return self.status == 'pending' and self.resolution in ('downgrade', 'none')
