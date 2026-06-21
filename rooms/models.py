"""
Rooms app — Room model.
Represents physical hotel rooms with status tracking.
"""
from django.db import models


class Room(models.Model):
    """
    Custom model representing a hotel room.
    Tracks type, floor, price, availability status and cleanliness.
    """
    TYPE_CHOICES = [
        ('dark-room',        'Dark Room'),
        ('studio-suite',     'Studio Suite'),
        ('loft-suite',       'Loft Suite'),
        ('family-studio',    'Family Studio'),
        ('family-suite',     'Family Suite'),
        ('family-ultimate',  'Ultimate Family Suite'),
        ('obsidian-suite',   'Obsidian Suite'),
        ('penthouse',        'Void Penthouse'),
    ]

    STATUS_CHOICES = [
        ('vacant',      'Vacant'),
        ('occupied',    'Occupied'),
        ('booked',      'Booked'),
        ('maintenance', 'Maintenance'),
    ]

    room_number  = models.CharField(max_length=10, unique=True)
    name         = models.CharField(max_length=100)
    room_type    = models.CharField(max_length=30, choices=TYPE_CHOICES)
    floor        = models.PositiveSmallIntegerField()
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='vacant')
    is_clean     = models.BooleanField(default=True)
    notes        = models.TextField(blank=True)
    description  = models.TextField(blank=True)
    max_guests   = models.PositiveSmallIntegerField(default=2)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['floor', 'room_number']
        verbose_name        = 'Room'
        verbose_name_plural = 'Rooms'

    def __str__(self):
        return f'Room {self.room_number} — {self.name}'

    def is_available(self):
        """Returns True if room can accept a new booking."""
        return self.status == 'vacant'
