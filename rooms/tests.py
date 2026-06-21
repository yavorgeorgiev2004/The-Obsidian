"""
Rooms app — automated tests.
Tests the Room model and the availability checking logic.
"""
from django.test import TestCase
from datetime import date, timedelta
from .models import Room
from .utils import is_room_available_for_dates, room_types_with_status


class RoomModelTest(TestCase):
    """Tests for the Room model."""

    def setUp(self):
        """Create a sample room before each test."""
        self.room = Room.objects.create(
            room_number='101', name='Test Room', room_type='dark-room',
            floor=1, price_per_night=420, max_guests=2,
        )

    def test_room_str(self):
        """The string representation includes the room number."""
        self.assertIn('101', str(self.room))

    def test_room_default_status_is_vacant(self):
        """A new room defaults to vacant and is available."""
        self.assertEqual(self.room.status, 'vacant')
        self.assertTrue(self.room.is_available())

    def test_maintenance_room_not_available(self):
        """A room is unavailable for dates that fall in a maintenance window."""
        from maintenance.models import MaintenanceLog
        today = date.today()
        # Create an active maintenance window covering the next few days
        MaintenanceLog.objects.create(
            room=self.room, category='plumbing',
            started=today, expected_ready=today + timedelta(days=3),
            status='active',
        )
        # A request inside that window is blocked
        self.assertFalse(
            is_room_available_for_dates(self.room, today, today + timedelta(days=2))
        )

    def test_room_free_after_maintenance_window(self):
        """A room becomes available again for dates after its maintenance window."""
        from maintenance.models import MaintenanceLog
        today = date.today()
        # Maintenance covers the next 3 days only
        MaintenanceLog.objects.create(
            room=self.room, category='plumbing',
            started=today, expected_ready=today + timedelta(days=3),
            status='active',
        )
        # A request well after the window is allowed, even though the log is active
        self.assertTrue(
            is_room_available_for_dates(self.room, today + timedelta(days=10), today + timedelta(days=12))
        )


class AvailabilityTest(TestCase):
    """Tests for the date-overlap availability logic."""

    def setUp(self):
        self.room = Room.objects.create(
            room_number='102', name='Test Suite', room_type='studio-suite',
            floor=1, price_per_night=580, max_guests=2,
        )

    def test_vacant_room_is_available(self):
        """A vacant room with no bookings is available for any dates."""
        today = date.today()
        self.assertTrue(
            is_room_available_for_dates(self.room, today, today + timedelta(days=3))
        )

    def test_room_types_summary(self):
        """The homepage summary returns a list with availability flags."""
        summary = room_types_with_status()
        self.assertTrue(any(rt['is_available'] for rt in summary))
