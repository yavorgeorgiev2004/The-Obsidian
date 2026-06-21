"""
Bookings app — automated tests.
Covers booking creation, the money calculations (total, deposit, paid,
balance), top-up logic, and availability after edits/cancellations.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from datetime import date, timedelta
from rooms.models import Room
from rooms.utils import is_room_available_for_dates
from .models import Booking


class BookingMoneyTest(TestCase):
    """Tests for the Booking model's money calculations."""

    def setUp(self):
        """Create a user and a room for the money tests."""
        self.user = User.objects.create_user(username='m@m.com', email='m@m.com', password='pw')
        self.room = Room.objects.create(
            room_number='301', name='Test Room', room_type='dark-room',
            floor=3, price_per_night=400, max_guests=2,
        )

    def test_grand_total_and_balance(self):
        """Totals and balance owed calculate correctly with no payment."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.room,
            check_in=today, check_out=today + timedelta(days=2),
        )
        booking.calculate_totals()
        # Two nights at 400 = 800 grand total, nothing paid yet
        self.assertEqual(booking.grand_total, 800)
        self.assertEqual(booking.balance_owed, 800)

    def test_deposit_is_quarter(self):
        """Deposit is 25% of the grand total."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.room,
            check_in=today, check_out=today + timedelta(days=2),
        )
        booking.calculate_totals()
        # 25% of 800 = 200
        self.assertEqual(booking.deposit_amount(), 200)

    def test_apply_payment_updates_paid_and_balance(self):
        """Applying a payment increases amount paid and lowers balance."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.room,
            check_in=today, check_out=today + timedelta(days=2),
        )
        booking.calculate_totals()
        booking.save()
        # Pay the 200 deposit
        booking.apply_payment(200)
        self.assertEqual(booking.amount_paid, 200)
        self.assertEqual(booking.balance_owed, 600)
        self.assertTrue(booking.deposit_paid)

    def test_top_up_due_after_increase(self):
        """A top-up is owed when the total rises after a deposit is paid."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.room,
            check_in=today, check_out=today + timedelta(days=2),
        )
        booking.calculate_totals()
        booking.save()
        booking.apply_payment(200)  # deposit on the 800 total

        # Extend the stay to 4 nights -> 1600 total, deposit now 400
        booking.check_out = today + timedelta(days=4)
        booking.calculate_totals()
        booking.save()
        # Already paid 200, new deposit 400, so 200 top-up is due
        self.assertEqual(booking.top_up_due(), 200)


class AvailabilityAfterChangeTest(TestCase):
    """Tests that editing or cancelling frees dates for other guests."""

    def setUp(self):
        self.user = User.objects.create_user(username='n@n.com', email='n@n.com', password='pw')
        self.room = Room.objects.create(
            room_number='302', name='Test Room 2', room_type='dark-room',
            floor=3, price_per_night=400, max_guests=2,
        )

    def test_cancelled_booking_frees_dates(self):
        """A cancelled booking no longer blocks its dates."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.room,
            check_in=today, check_out=today + timedelta(days=3),
            status='confirmed',
        )
        # While confirmed, the room is not available for those dates
        self.assertFalse(
            is_room_available_for_dates(self.room, today, today + timedelta(days=3))
        )
        # After cancelling, the same dates become available again
        booking.status = 'cancelled'
        booking.save()
        self.assertTrue(
            is_room_available_for_dates(self.room, today, today + timedelta(days=3))
        )


class CreditAndBalanceTest(TestCase):
    """Tests for overpayment credit and the floored balance."""

    def setUp(self):
        """Create a user and two rooms at different prices."""
        self.user = User.objects.create_user(username='c@c.com', email='c@c.com', password='pw')
        self.expensive = Room.objects.create(
            room_number='901', name='Pricey', room_type='penthouse',
            floor=9, price_per_night=1000, max_guests=2,
        )
        self.cheap = Room.objects.create(
            room_number='101', name='Cheap', room_type='dark-room',
            floor=1, price_per_night=100, max_guests=2,
        )

    def test_balance_never_negative(self):
        """Overpaying floors the balance at zero, never negative."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.cheap,
            check_in=today, check_out=today + timedelta(days=1),
        )
        booking.calculate_totals()
        booking.save()
        # Pay far more than the total
        booking.apply_payment(500)
        # 1 night at 100 = 100 total; balance must be 0, not -400
        self.assertEqual(booking.balance_owed, 0)

    def test_overpayment_returned_for_credit(self):
        """calculate_totals reports any overpayment for crediting."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.expensive,
            check_in=today, check_out=today + timedelta(days=2),
        )
        booking.calculate_totals()  # 2 nights x 1000 = 2000
        booking.amount_paid = 2000
        booking.save()
        # Switch to the cheap room and recalc — now overpaid
        booking.room = self.cheap
        overpayment = booking.calculate_totals()  # 2 nights x 100 = 200
        # Paid 2000, new total 200, so 1800 overpaid
        self.assertEqual(overpayment, 1800)

    def test_pending_payment_status_default(self):
        """A booking can be created awaiting payment."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.cheap,
            check_in=today, check_out=today + timedelta(days=1),
            status='pending-payment',
        )
        # The status is recorded and is not yet confirmed
        self.assertEqual(booking.status, 'pending-payment')
        self.assertFalse(booking.deposit_paid)

    def test_fully_paid_booking_needs_no_payment(self):
        """A fully paid booking reports nothing due, preventing a zero charge."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.cheap,
            check_in=today, check_out=today + timedelta(days=1),
            status='pending-payment',
        )
        booking.calculate_totals(); booking.save()
        booking.apply_payment(booking.grand_total)
        # Once fully paid, no payment is due and the amount due now is zero
        self.assertFalse(booking.needs_payment())
        self.assertEqual(booking.amount_due_now(), 0)
        self.assertTrue(booking.is_fully_paid())

    def test_amount_due_now_never_negative(self):
        """Amount due now is floored at zero even when overpaid."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.cheap,
            check_in=today, check_out=today + timedelta(days=1),
            status='pending-payment',
        )
        booking.calculate_totals(); booking.save()
        # Pay more than the deposit; amount due now must not go negative
        booking.apply_payment(booking.grand_total)
        self.assertGreaterEqual(booking.amount_due_now(), 0)


class CreditAccountTest(TestCase):
    """Tests for the UserProfile credit balance helpers."""

    def setUp(self):
        self.user = User.objects.create_user(username='cr@cr.com', email='cr@cr.com', password='pw')

    def test_add_and_use_credit(self):
        """Credit can be added and then spent, capped at the balance."""
        profile = self.user.profile
        profile.add_credit(300)
        self.assertEqual(profile.credit_balance, 300)
        # Using 100 leaves 200
        applied = profile.use_credit(100)
        self.assertEqual(applied, 100)
        self.assertEqual(profile.credit_balance, 200)
        # Using more than available only spends what is there
        applied = profile.use_credit(500)
        self.assertEqual(applied, 200)
        self.assertEqual(profile.credit_balance, 0)
