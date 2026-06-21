"""
Tests for the concierge app.

Cover the negotiation flow (guest submits, staff propose, guest confirms),
the form validation, and that guests cannot reach the staff manage view.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import ConciergeRequest
from .forms import ConciergeRequestForm


class ConciergeFormTest(TestCase):
    """Tests for the request form validation."""

    def test_detail_must_be_substantial(self):
        """A very short detail is rejected by the form."""
        form = ConciergeRequestForm(data={'request_type': 'restaurant', 'detail': 'hi'})
        # Detail under ten characters should fail validation
        self.assertFalse(form.is_valid())
        self.assertIn('detail', form.errors)

    def test_valid_request_passes(self):
        """A complete request with enough detail validates."""
        form = ConciergeRequestForm(data={
            'request_type': 'restaurant',
            'detail': 'A quiet corner table for two for our anniversary',
        })
        self.assertTrue(form.is_valid())


class ConciergeFlowTest(TestCase):
    """Tests for the guest/staff negotiation flow."""

    def setUp(self):
        """Create a guest, a receptionist, and a pending request."""
        self.guest = User.objects.create_user(username='cg@cg.com', email='cg@cg.com', password='pw')
        self.staff = User.objects.create_user(username='cs@cs.com', email='cs@cs.com', password='pw')
        self.staff.profile.role = 'receptionist'
        self.staff.profile.save()
        self.req = ConciergeRequest.objects.create(
            guest=self.guest, request_type='restaurant',
            detail='Table for two on the rooftop terrace',
            requested_time=timezone.now() + timedelta(days=3),
            status='pending',
        )

    def test_staff_propose_then_guest_confirm(self):
        """Staff propose a time, the guest confirms, and it is set."""
        self.client.login(username='cs@cs.com', password='pw')
        proposed = (timezone.now() + timedelta(days=3, hours=2)).strftime('%Y-%m-%dT%H:%M')
        self.client.post(f'/concierge/{self.req.pk}/manage/', {'action': 'propose', 'proposed_time': proposed})
        self.req.refresh_from_db()
        # The request now awaits the guest's decision
        self.assertEqual(self.req.status, 'proposed')

        # The guest confirms the proposed time
        self.client.logout()
        self.client.login(username='cg@cg.com', password='pw')
        self.client.post(f'/concierge/{self.req.pk}/respond/', {'action': 'confirm'})
        self.req.refresh_from_db()
        # The request is confirmed with a final agreed time
        self.assertEqual(self.req.status, 'confirmed')
        self.assertIsNotNone(self.req.confirmed_time)

    def test_guest_cannot_manage(self):
        """A guest is blocked from the staff manage view."""
        self.client.login(username='cg@cg.com', password='pw')
        response = self.client.get(f'/concierge/{self.req.pk}/manage/')
        # Guests are redirected away from the staff-only view
        self.assertEqual(response.status_code, 302)
