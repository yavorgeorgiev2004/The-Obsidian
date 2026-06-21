"""
Accounts app — automated tests.
Tests UserProfile auto-creation and the loyalty tier logic.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileTest(TestCase):
    """Tests for the UserProfile model and signals."""

    def test_profile_created_on_user_creation(self):
        """A UserProfile is automatically created with each new User."""
        user = User.objects.create_user(username='a@a.com', email='a@a.com', password='pw')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.role, 'guest')

    def test_loyalty_tier_updates(self):
        """Loyalty tier updates correctly based on points thresholds."""
        user = User.objects.create_user(username='b@b.com', email='b@b.com', password='pw')
        profile = user.profile
        profile.loyalty_points = 2500
        profile.update_loyalty_tier()
        self.assertEqual(profile.loyalty_tier, 'gold')
        profile.loyalty_points = 6000
        profile.update_loyalty_tier()
        self.assertEqual(profile.loyalty_tier, 'diamond')

    def test_is_staff_member(self):
        """The is_staff_member helper correctly identifies staff."""
        user = User.objects.create_user(username='c@c.com', email='c@c.com', password='pw')
        user.profile.role = 'receptionist'
        self.assertTrue(user.profile.is_staff_member())
        user.profile.role = 'guest'
        self.assertFalse(user.profile.is_staff_member())
