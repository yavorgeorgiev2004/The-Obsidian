"""
Accounts app — UserProfile model extending Django's built-in User.
Adds role-based access control and loyalty points for the Diamond Circle.
"""
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Custom model extending User with role and loyalty data.
    One-to-one relationship with Django's built-in User model.
    """
    ROLE_CHOICES = [
        ('guest',        'Guest'),
        ('receptionist', 'Receptionist'),
        ('manager',      'Manager'),
    ]

    TIER_CHOICES = [
        ('obsidian', 'Obsidian'),
        ('gold',     'Gold'),
        ('diamond',  'Diamond'),
    ]

    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default='guest')
    phone        = models.CharField(max_length=20, blank=True)
    loyalty_points = models.PositiveIntegerField(default=0)
    loyalty_tier   = models.CharField(max_length=20, choices=TIER_CHOICES, default='obsidian')

    # Account credit — money the guest has overpaid (for example by editing
    # a booking down to a cheaper total after paying). It is held as credit
    # and applied automatically to future bookings. The guest can also ask
    # reception to return it in person; no automatic cash refund is issued.
    credit_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.role})'

    def is_staff_member(self):
        """Returns True if user is receptionist or manager."""
        return self.role in ('receptionist', 'manager')

    def add_credit(self, amount):
        """Add an overpaid amount to the guest's credit balance."""
        # Only positive amounts ever increase the credit balance
        if amount > 0:
            self.credit_balance += amount
            self.save()

    def use_credit(self, amount):
        """
        Spend up to `amount` of credit against a new charge. Returns the
        amount of credit actually applied, capped at the available balance.
        """
        # Apply whichever is smaller: the credit available or the amount needed
        applied = min(self.credit_balance, amount)
        if applied > 0:
            self.credit_balance -= applied
            self.save()
        return applied

    def update_loyalty_tier(self):
        """Update tier based on current points balance."""
        if self.loyalty_points >= 5000:
            self.loyalty_tier = 'diamond'
        elif self.loyalty_points >= 2000:
            self.loyalty_tier = 'gold'
        else:
            self.loyalty_tier = 'obsidian'
        self.save()
