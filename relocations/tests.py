"""
Tests for the relocations app.

Cover the compensation maths (free nights, bonus), the resolution-finding
logic (same / upgrade / downgrade / none), and that guests are credited
correctly when they choose to cancel for credit.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from datetime import date, timedelta
from rooms.models import Room
from bookings.models import Booking
from .models import RelocationOffer
from .utils import free_nights_for, bonus_credit, find_relocation


class CompensationMathTest(TestCase):
    """Tests for the free-nights and bonus calculations."""

    def setUp(self):
        """Create a user and a priced room for the maths tests."""
        self.user = User.objects.create_user(username='r@r.com', email='r@r.com', password='pw')
        self.room = Room.objects.create(
            room_number='701', name='Test', room_type='penthouse',
            floor=7, price_per_night=500, max_guests=2,
        )

    def test_short_stay_one_free_night(self):
        """A stay under four nights earns one free night."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.room,
            check_in=today, check_out=today + timedelta(days=2),
        )
        # Two nights is a short stay, so one free night
        self.assertEqual(free_nights_for(booking), 1)
        # Bonus is one night at the room rate
        self.assertEqual(bonus_credit(booking), 500)

    def test_long_stay_two_free_nights(self):
        """A stay of four or more nights earns two free nights."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.room,
            check_in=today, check_out=today + timedelta(days=5),
        )
        # Five nights is a long stay, so two free nights
        self.assertEqual(free_nights_for(booking), 2)
        # Bonus is two nights at the room rate
        self.assertEqual(bonus_credit(booking), 1000)


class ResolutionFindingTest(TestCase):
    """Tests that find_relocation picks the right kind of move."""

    def setUp(self):
        self.user = User.objects.create_user(username='r2@r.com', email='r2@r.com', password='pw')
        # Two rooms of the same cheap type, one expensive room
        self.cheap_a = Room.objects.create(room_number='201', name='Cheap A', room_type='dark-room', floor=2, price_per_night=200, max_guests=2)
        self.cheap_b = Room.objects.create(room_number='202', name='Cheap B', room_type='dark-room', floor=2, price_per_night=200, max_guests=2)
        self.expensive = Room.objects.create(room_number='901', name='Pricey', room_type='penthouse', floor=9, price_per_night=2000, max_guests=2)

    def test_finds_same_type(self):
        """When another room of the same type is free, that is chosen."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.cheap_a,
            check_in=today, check_out=today + timedelta(days=2),
        )
        resolution, new_room = find_relocation(booking)
        # The other cheap room should be offered as a same-type move
        self.assertEqual(resolution, 'same')
        self.assertEqual(new_room, self.cheap_b)

    def test_finds_downgrade_for_top_tier(self):
        """The most expensive room can only be downgraded."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.expensive,
            check_in=today, check_out=today + timedelta(days=2),
        )
        resolution, new_room = find_relocation(booking)
        # No equal or higher room exists, so it must be a downgrade
        self.assertEqual(resolution, 'downgrade')


class GuestCreditChoiceTest(TestCase):
    """Tests the credit outcome when a guest cancels a disrupted booking."""

    def setUp(self):
        self.user = User.objects.create_user(username='r3@r.com', email='r3@r.com', password='pw')
        self.room = Room.objects.create(room_number='301', name='Room', room_type='penthouse', floor=3, price_per_night=400, max_guests=2)

    def test_credit_choice_refunds_paid_plus_bonus(self):
        """Choosing credit returns the amount paid plus the bonus."""
        today = date.today()
        booking = Booking.objects.create(
            guest=self.user, room=self.room,
            check_in=today, check_out=today + timedelta(days=2),
        )
        booking.calculate_totals()
        booking.apply_payment(booking.grand_total)  # pay in full
        # Build a pending no-availability offer with a one-night bonus
        offer = RelocationOffer.objects.create(
            booking=booking, guest=self.user, original_room=self.room,
            resolution='none', free_nights=1, bonus_credit=400, status='pending',
        )
        self.client.login(username='r3@r.com', password='pw')
        self.client.post(f'/relocations/offer/{offer.pk}/decide/', {'choice': 'credit'})
        self.user.profile.refresh_from_db()
        booking.refresh_from_db()
        # Paid 800 (2 nights x 400) + 400 bonus = 1200 credit, booking cancelled
        self.assertEqual(self.user.profile.credit_balance, 1200)
        self.assertEqual(booking.status, 'cancelled')


class StaffRecordDecisionTest(TestCase):
    """Tests that staff can record a guest's decision and guests cannot."""

    def setUp(self):
        """Create a guest, a staff user, a room and a paid booking."""
        self.guest = User.objects.create_user(username='g4@g.com', email='g4@g.com', password='pw')
        self.staff = User.objects.create_user(username='s4@s.com', email='s4@s.com', password='pw')
        # Make the staff user a receptionist via their profile
        self.staff.profile.role = 'receptionist'
        self.staff.profile.save()
        self.room = Room.objects.create(room_number='401', name='Room', room_type='penthouse', floor=4, price_per_night=300, max_guests=2)
        today = date.today()
        self.booking = Booking.objects.create(
            guest=self.guest, room=self.room,
            check_in=today, check_out=today + timedelta(days=2),
        )
        self.booking.calculate_totals()
        self.booking.apply_payment(self.booking.grand_total)
        self.offer = RelocationOffer.objects.create(
            booking=self.booking, guest=self.guest, original_room=self.room,
            resolution='none', free_nights=1, bonus_credit=300, status='pending',
        )

    def test_staff_can_record_credit(self):
        """A receptionist can record a credit decision for the guest."""
        self.client.login(username='s4@s.com', password='pw')
        self.client.post(f'/relocations/offer/{self.offer.pk}/record/', {'choice': 'credit'})
        self.guest.profile.refresh_from_db()
        self.booking.refresh_from_db()
        # Paid 600 (2 nights x 300) + 300 bonus = 900 credit, booking cancelled
        self.assertEqual(self.guest.profile.credit_balance, 900)
        self.assertEqual(self.booking.status, 'cancelled')

    def test_guest_cannot_record(self):
        """A guest is blocked from the staff record endpoint."""
        self.client.login(username='g4@g.com', password='pw')
        response = self.client.post(f'/relocations/offer/{self.offer.pk}/record/', {'choice': 'credit'})
        # Guests are redirected away, not allowed to record staff decisions
        self.assertEqual(response.status_code, 302)
        self.offer.refresh_from_db()
        # The offer must remain pending since the guest could not act here
        self.assertEqual(self.offer.status, 'pending')
