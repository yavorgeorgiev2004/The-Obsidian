"""
Tests for the maintenance app.

Cover the default-window calculation, the escalation levels, the
date-bounded availability behaviour, the audit logging, and the
manager-only visibility of the full audit trail.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from rooms.models import Room
from rooms.utils import is_room_available_for_dates
from .models import MaintenanceLog, StaffActionLog, log_action


class MaintenanceWindowTest(TestCase):
    """Tests for the maintenance default window and escalation."""

    def setUp(self):
        """Create a room to attach maintenance logs to."""
        self.room = Room.objects.create(
            room_number='801', name='Test', room_type='loft-suite',
            floor=8, price_per_night=300, max_guests=2,
        )

    def test_default_ready_date_from_category(self):
        """Each category sets a default ready date a fixed number of days out."""
        today = date.today()
        # Plumbing defaults to three days
        ready = MaintenanceLog.default_ready_date('plumbing', today)
        self.assertEqual(ready, today + timedelta(days=3))

    def test_escalation_overdue(self):
        """An active log past its expected date is overdue."""
        today = date.today()
        log = MaintenanceLog.objects.create(
            room=self.room, category='minor',
            started=today - timedelta(days=3),
            expected_ready=today - timedelta(days=1),
            status='active',
        )
        # Expected-ready was yesterday, so it is overdue
        self.assertEqual(log.escalation(), 'overdue')

    def test_escalation_due_soon(self):
        """A log within a day of its expected date is due soon."""
        today = date.today()
        log = MaintenanceLog.objects.create(
            room=self.room, category='minor',
            started=today, expected_ready=today,
            status='active',
        )
        # Expected-ready is today, so it is due soon
        self.assertEqual(log.escalation(), 'due-soon')


class DateBoundedAvailabilityTest(TestCase):
    """Tests that maintenance blocks only its own date window."""

    def setUp(self):
        self.room = Room.objects.create(
            room_number='802', name='Test2', room_type='loft-suite',
            floor=8, price_per_night=300, max_guests=2,
        )
        today = date.today()
        # Maintenance covering the next three days
        MaintenanceLog.objects.create(
            room=self.room, category='plumbing',
            started=today, expected_ready=today + timedelta(days=3),
            status='active',
        )

    def test_blocked_inside_window(self):
        """Dates inside the maintenance window are unavailable."""
        today = date.today()
        self.assertFalse(
            is_room_available_for_dates(self.room, today, today + timedelta(days=2))
        )

    def test_free_after_window(self):
        """Dates after the maintenance window are available."""
        today = date.today()
        self.assertTrue(
            is_room_available_for_dates(self.room, today + timedelta(days=10), today + timedelta(days=12))
        )


class AuditLogTest(TestCase):
    """Tests for the staff action audit trail and its visibility."""

    def setUp(self):
        self.manager = User.objects.create_user(username='m@m.com', email='m@m.com', password='pw')
        self.manager.profile.role = 'manager'
        self.manager.profile.save()
        self.receptionist = User.objects.create_user(username='re@re.com', email='re@re.com', password='pw')
        self.receptionist.profile.role = 'receptionist'
        self.receptionist.profile.save()
        self.room = Room.objects.create(
            room_number='803', name='Test3', room_type='loft-suite',
            floor=8, price_per_night=300, max_guests=2,
        )

    def test_log_action_records_staff(self):
        """log_action writes an attributable audit record."""
        log_action(self.receptionist, 'clean', 'Room 803 marked clean', room=self.room)
        entry = StaffActionLog.objects.first()
        # The record names the staff member and the action
        self.assertEqual(entry.staff, self.receptionist)
        self.assertEqual(entry.action, 'clean')

    def test_manager_sees_audit_log(self):
        """A manager is granted access to the full audit log view."""
        from django.test import override_settings
        self.client.login(username='m@m.com', password='pw')
        # Use the simple static storage in the test so the template's static
        # references do not require a collectstatic manifest to be present.
        with override_settings(STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        }):
            response = self.client.get('/maintenance/audit/')
        self.assertEqual(response.status_code, 200)

    def test_receptionist_blocked_from_audit_log(self):
        """A receptionist cannot open the full audit log (manager-only)."""
        self.client.login(username='re@re.com', password='pw')
        response = self.client.get('/maintenance/audit/')
        # Receptionists are redirected away from the manager-only full log
        self.assertEqual(response.status_code, 302)
