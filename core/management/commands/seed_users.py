"""
Management command — create the demo accounts for testing each role.
Run with: python manage.py seed_users
Creates a guest, a receptionist and a manager with known passwords so
all three dashboards can be tested immediately.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Creates demo guest, receptionist and manager accounts.'

    def handle(self, *args, **options):
        # Each tuple holds the demo account details and the role to assign
        demo_accounts = [
            ('guest@obsidian.com',     'guest123',   'guest',        'James',     'Holloway'),
            ('reception@obsidian.com', 'staff123',   'receptionist', 'Elena',     'Vasquez'),
            ('manager@obsidian.com',   'manager123', 'manager',      'Alexandra', 'Reid'),
        ]

        # Walk each demo account and create it if it does not already exist
        for email, password, role, first, last in demo_accounts:
            # Skip creation if a user with this email already exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(f'Already exists: {email}')
                continue

            # Create the user; the username is set to the email for simplicity
            user = User.objects.create_user(
                username=email, email=email, password=password,
                first_name=first, last_name=last,
            )

            # The signal auto-creates a profile; set its role to match
            user.profile.role = role
            user.profile.save()
            self.stdout.write(self.style.SUCCESS(f'Created {role}: {email} / {password}'))

        self.stdout.write(self.style.SUCCESS('Demo users ready.'))
