"""
Models for the maintenance app.

MaintenanceLog records a single maintenance event on a room: why it was
taken out of service, when it started, when it is expected to be ready,
and who set and cleared it. StaffActionLog records an audit trail of
consequential staff actions so every change is attributable to a person.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rooms.models import Room


class MaintenanceLog(models.Model):
    """
    A maintenance event on one room. The expected_ready date bounds the
    period the room is blocked for; availability checks treat only the
    started..expected_ready window as unavailable, so the room frees for
    later dates automatically without waiting to be manually cleared.
    """

    # The kinds of issue a room can be taken out of service for. Each
    # category carries a realistic default number of days to resolve.
    CATEGORY_CHOICES = [
        ('minor',      'Minor (same day)'),
        ('furniture',  'Broken Furniture (1-2 days)'),
        ('plumbing',   'Plumbing (2-3 days)'),
        ('electrical', 'Electrical (2-3 days)'),
        ('deepclean',  'Deep Clean / Pest (1-2 days)'),
        ('major',      'Major / Structural (7+ days)'),
    ]

    # Default resolution windows in days, keyed by category. Used to set the
    # initial expected_ready date, which staff may then adjust.
    DEFAULT_DAYS = {
        'minor': 1,
        'furniture': 2,
        'plumbing': 3,
        'electrical': 3,
        'deepclean': 2,
        'major': 7,
    }

    # Whether the event is still in effect or has been cleared.
    STATUS_CHOICES = [
        ('active',  'Active'),
        ('cleared', 'Cleared'),
    ]

    # The room affected and the category of issue.
    room        = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='maintenance_logs')
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    notes       = models.TextField(blank=True)

    # The window the room is out of service for.
    started     = models.DateField(default=timezone.now)
    expected_ready = models.DateField()

    # Current state and the times it changed.
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at  = models.DateTimeField(auto_now_add=True)
    cleared_at  = models.DateTimeField(null=True, blank=True)

    # Accountability: which staff member set and later cleared the event.
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='maintenance_created')
    cleared_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_cleared')

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Maintenance Log'
        verbose_name_plural = 'Maintenance Logs'

    def __str__(self):
        return f'{self.room.room_number} — {self.get_category_display()} ({self.status})'

    @classmethod
    def default_ready_date(cls, category, start=None):
        """Return the default expected-ready date for a category from a start day."""
        # Add the category's default day count to the start date
        start = start or timezone.now().date()
        return start + timedelta(days=cls.DEFAULT_DAYS.get(category, 1))

    def escalation(self):
        """
        Return the urgency level of an active maintenance event by comparing
        its expected-ready date to today: 'overdue' if past, 'due-soon' if
        within a day, otherwise 'upcoming'. Cleared events return 'cleared'.
        """
        # Cleared events have no urgency
        if self.status == 'cleared':
            return 'cleared'
        today = timezone.now().date()
        # Past the expected date and still active means overdue
        if today > self.expected_ready:
            return 'overdue'
        # Within one day of the expected date means it needs attention soon
        if (self.expected_ready - today).days <= 1:
            return 'due-soon'
        return 'upcoming'


class StaffActionLog(models.Model):
    """
    An audit record of a consequential staff action. One row is written
    each time a staff member checks a guest in or out, changes a room's
    cleanliness or maintenance, or records a guest's relocation decision,
    so every change is attributable to a named person at a known time.
    """

    # The kinds of action that are logged for accountability.
    ACTION_CHOICES = [
        ('check-in',      'Checked In'),
        ('check-out',     'Checked Out'),
        ('clean',         'Marked Clean'),
        ('dirty',         'Marked Needs Cleaning'),
        ('maint-set',     'Set Maintenance'),
        ('maint-extend',  'Extended Maintenance'),
        ('maint-clear',   'Cleared Maintenance'),
        ('relocation',    'Recorded Relocation Decision'),
    ]

    # Who acted, what they did, and a short description of the target.
    staff       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='action_logs')
    action      = models.CharField(max_length=20, choices=ACTION_CHOICES)
    detail      = models.CharField(max_length=255)

    # Optional links to the room or booking the action concerned, so the
    # last action on a given room can be looked up for receptionists.
    room        = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='action_logs')

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Staff Action Log'
        verbose_name_plural = 'Staff Action Logs'

    def __str__(self):
        who = self.staff.get_full_name() or self.staff.email if self.staff else 'Unknown'
        return f'{who} — {self.get_action_display()} ({self.created_at:%Y-%m-%d %H:%M})'


def log_action(staff, action, detail, room=None):
    """
    Write a staff action to the audit trail. Called from the staff views
    after each consequential change so the log captures who did what.
    """
    # Create the audit record for this action
    StaffActionLog.objects.create(staff=staff, action=action, detail=detail, room=room)
