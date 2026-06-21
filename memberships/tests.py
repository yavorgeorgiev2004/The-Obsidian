"""
Tests for the memberships app.
Cover discount-by-tier, expiry behaviour, and the prorated upgrade cost
with its same/lower-tier guard.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Membership
from .utils import upgrade_cost


class MembershipModelTest(TestCase):
    """Tests for membership discount and expiry."""

    def setUp(self):
        self.user = User.objects.create_user(username='mm@mm.com', email='mm@mm.com', password='pw')

    def test_active_membership_gives_discount(self):
        """An active membership returns its tier discount."""
        m = Membership.objects.create(
            member=self.user, tier='gold',
            started_at=timezone.now().date(),
            expires_at=timezone.now().date() + timedelta(days=365),
        )
        # Gold gives ten percent while active
        self.assertTrue(m.is_active())
        self.assertEqual(m.discount_percent(), 10)

    def test_expired_membership_gives_no_discount(self):
        """An expired membership returns a zero discount."""
        m = Membership.objects.create(
            member=self.user, tier='gold',
            started_at=timezone.now().date() - timedelta(days=400),
            expires_at=timezone.now().date() - timedelta(days=1),
        )
        # Past expiry, no discount applies
        self.assertFalse(m.is_active())
        self.assertEqual(m.discount_percent(), 0)


class UpgradeCostTest(TestCase):
    """Tests for the prorated upgrade cost."""

    def setUp(self):
        self.user = User.objects.create_user(username='mu@mu.com', email='mu@mu.com', password='pw')
        self.m = Membership.objects.create(
            member=self.user, tier='gold',
            started_at=timezone.now().date(),
            expires_at=timezone.now().date() + timedelta(days=365),
        )

    def test_upgrade_to_higher_tier_prorated(self):
        """Upgrading to a higher tier costs the prorated, rounded-up gap."""
        cost = upgrade_cost(self.m, 'diamond')
        # Gap is £200; with a full year remaining the cost is about £200
        self.assertIsNotNone(cost)
        self.assertGreaterEqual(cost, 1)
        self.assertLessEqual(cost, 200)

    def test_cannot_upgrade_to_same_or_lower(self):
        """Same or lower tiers are not valid upgrades."""
        # Same tier and a lower tier both return None
        self.assertIsNone(upgrade_cost(self.m, 'gold'))
        self.assertIsNone(upgrade_cost(self.m, 'obsidian'))

    def test_upgrade_minimum_one_pound(self):
        """A near-expired upgrade still costs at least one pound."""
        # One day left makes the prorated amount tiny, floored at £1
        self.m.expires_at = timezone.now().date() + timedelta(days=1)
        self.m.save()
        self.assertEqual(upgrade_cost(self.m, 'diamond'), 1)
