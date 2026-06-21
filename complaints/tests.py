"""
Tests for the complaints app.
Cover form validation, the open->resolved workflow, and that only
managers can award account credit when resolving.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Complaint
from .forms import ComplaintForm


class ComplaintFormTest(TestCase):
    """Tests for complaint form validation."""

    def setUp(self):
        self.user = User.objects.create_user(username='cf@cf.com', email='cf@cf.com', password='pw')

    def test_detail_required_length(self):
        """A too-short detail is rejected."""
        form = ComplaintForm(data={'category': 'noise', 'detail': 'no'}, user=self.user)
        self.assertFalse(form.is_valid())

    def test_valid_complaint(self):
        """A complaint with enough detail validates."""
        form = ComplaintForm(data={'category': 'noise', 'detail': 'There was loud noise all night long'}, user=self.user)
        self.assertTrue(form.is_valid())


class ComplaintWorkflowTest(TestCase):
    """Tests for the staff workflow and manager-only credit."""

    def setUp(self):
        self.guest = User.objects.create_user(username='cg@cg.com', email='cg@cg.com', password='pw')
        self.recep = User.objects.create_user(username='cr@cr.com', email='cr@cr.com', password='pw')
        self.recep.profile.role = 'receptionist'; self.recep.profile.save()
        self.manager = User.objects.create_user(username='cm@cm.com', email='cm@cm.com', password='pw')
        self.manager.profile.role = 'manager'; self.manager.profile.save()
        self.complaint = Complaint.objects.create(
            guest=self.guest, category='noise',
            detail='Loud noise next door all night', status='in-progress',
        )

    def test_receptionist_cannot_award_credit(self):
        """A receptionist resolving a complaint awards no credit."""
        self.client.login(username='cr@cr.com', password='pw')
        self.client.post(f'/complaints/{self.complaint.pk}/manage/',
                         {'action': 'resolve', 'resolution': 'Handled', 'credit_awarded': '50'})
        self.complaint.refresh_from_db()
        self.guest.profile.refresh_from_db()
        # No credit is awarded by a receptionist
        self.assertEqual(self.complaint.credit_awarded, Decimal('0'))
        self.assertEqual(self.guest.profile.credit_balance, Decimal('0'))

    def test_manager_awards_credit(self):
        """A manager resolving a complaint can award account credit."""
        self.client.login(username='cm@cm.com', password='pw')
        self.client.post(f'/complaints/{self.complaint.pk}/manage/',
                         {'action': 'resolve', 'resolution': 'Comped', 'credit_awarded': '60'})
        self.complaint.refresh_from_db()
        self.guest.profile.refresh_from_db()
        # The manager's award is applied to the guest's balance
        self.assertEqual(self.complaint.status, 'resolved')
        self.assertEqual(self.guest.profile.credit_balance, Decimal('60'))

    def test_guest_cannot_see_queue(self):
        """A guest cannot open the staff complaints queue."""
        self.client.login(username='cg@cg.com', password='pw')
        response = self.client.get('/complaints/queue/')
        self.assertEqual(response.status_code, 302)
