"""
Packages app — Package model.
Pre-order add-ons guests can attach to a booking.
"""
from django.db import models


class Package(models.Model):
    """
    Custom model for pre-order packages (food, spa, occasion).
    Guests select these during the booking process.
    """
    CATEGORY_CHOICES = [
        ('food',     'Food & Drink'),
        ('spa',      'Spa'),
        ('occasion', 'Occasion'),
    ]

    package_id   = models.CharField(max_length=50, unique=True)
    name         = models.CharField(max_length=200)
    category     = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description  = models.TextField()
    price        = models.DecimalField(max_digits=8, decimal_places=2)
    icon         = models.CharField(max_length=10, blank=True, help_text='Emoji icon')
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'price']
        verbose_name        = 'Package'
        verbose_name_plural = 'Packages'

    def __str__(self):
        return f'{self.name} — £{self.price}'
