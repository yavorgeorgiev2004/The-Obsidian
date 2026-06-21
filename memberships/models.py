"""
Models for the memberships app.

A Membership is a one-off yearly paid tier that grants a room-rate
discount. It does not auto-renew: when it expires the discount stops and
the member renews manually. Members may upgrade to a higher tier mid-term
by paying a prorated difference.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class Membership(models.Model):
    """
    A guest's membership at one of three tiers. The expiry is one year from
    purchase or renewal; an expired membership grants no discount until the
    member renews. Each tier carries a yearly price and a booking discount.
    """

    # Tier definitions: yearly price and the room-rate discount percentage.
    TIER_CHOICES = [
        ('obsidian', 'Obsidian'),
        ('gold',     'Gold'),
        ('diamond',  'Diamond'),
    ]

    # Yearly price per tier, in pounds
    TIER_PRICE = {
        'obsidian': Decimal('195'),
        'gold':     Decimal('295'),
        'diamond':  Decimal('495'),
    }

    # Room-rate discount percentage per tier
    TIER_DISCOUNT = {
        'obsidian': 5,
        'gold':     10,
        'diamond':  15,
    }

    # Ranking used to compare tiers for upgrade rules (higher is better)
    TIER_RANK = {'obsidian': 1, 'gold': 2, 'diamond': 3}

    # One membership per user; the tier and its validity window
    member     = models.OneToOneField(User, on_delete=models.CASCADE, related_name='membership')
    tier       = models.CharField(max_length=20, choices=TIER_CHOICES)
    started_at = models.DateField(default=timezone.now)
    expires_at = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Membership'
        verbose_name_plural = 'Memberships'

    def __str__(self):
        return f'{self.member.email} — {self.get_tier_display()} ({"active" if self.is_active() else "expired"})'

    def is_active(self):
        """Return True when the membership has not yet expired."""
        # Active while today is on or before the expiry date
        return timezone.now().date() <= self.expires_at

    def discount_percent(self):
        """Return the discount percentage if active, otherwise zero."""
        # An expired membership grants no discount
        if not self.is_active():
            return 0
        return self.TIER_DISCOUNT.get(self.tier, 0)

    def days_remaining(self):
        """Return whole days left until expiry, never negative."""
        # Counted from the start of today so partial days count in full
        delta = (self.expires_at - timezone.now().date()).days
        return max(delta, 0)

    @classmethod
    def price_for(cls, tier):
        """Return the yearly price for a tier."""
        return cls.TIER_PRICE.get(tier, Decimal('0'))
