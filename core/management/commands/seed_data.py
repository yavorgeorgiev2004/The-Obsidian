"""
Management command — seed the database with the initial rooms and
packages so the platform has content to display. Run with:
    python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from rooms.models import Room
from packages.models import Package


class Command(BaseCommand):
    help = 'Seeds the database with rooms and pre-order packages.'

    def handle(self, *args, **options):
        # Seed rooms only if the table is currently empty
        if Room.objects.exists():
            self.stdout.write('Rooms already exist — skipping room seed.')
        else:
            self._seed_rooms()

        # Seed packages only if the table is currently empty
        if Package.objects.exists():
            self.stdout.write('Packages already exist — skipping package seed.')
        else:
            self._seed_packages()

        self.stdout.write(self.style.SUCCESS('Seed complete.'))

    def _seed_rooms(self):
        """Create the 21 rooms across floors 2 to 6."""
        rooms = [
            ('201', 'Dark Room', 'dark-room', 2, 420, 2),
            ('202', 'Dark Room', 'dark-room', 2, 420, 2),
            ('203', 'Studio Suite', 'studio-suite', 2, 580, 2),
            ('204', 'Dark Room', 'dark-room', 2, 420, 2),
            ('205', 'Studio Suite', 'studio-suite', 2, 580, 2),
            ('206', 'Dark Room', 'dark-room', 2, 420, 2),
            ('301', 'Studio Suite', 'studio-suite', 3, 580, 2),
            ('302', 'Dark Room', 'dark-room', 3, 420, 2),
            ('303', 'Loft Suite', 'loft-suite', 3, 850, 3),
            ('304', 'Dark Room', 'dark-room', 3, 420, 2),
            ('305', 'Studio Suite', 'studio-suite', 3, 580, 2),
            ('306', 'Loft Suite', 'loft-suite', 3, 850, 3),
            ('401', 'Loft Suite', 'loft-suite', 4, 850, 3),
            ('402', 'Family Studio', 'family-studio', 4, 580, 4),
            ('403', 'Loft Suite', 'loft-suite', 4, 850, 3),
            ('404', 'Family Suite', 'family-suite', 4, 1100, 5),
            ('405', 'Loft Suite', 'loft-suite', 4, 850, 3),
            ('501', 'Obsidian Suite', 'obsidian-suite', 5, 1500, 4),
            ('502', 'Ultimate Family Suite', 'family-ultimate', 5, 1800, 6),
            ('503', 'Obsidian Suite', 'obsidian-suite', 5, 1500, 4),
            ('R01', 'Void Penthouse', 'penthouse', 6, 4000, 4),
        ]
        # Create each room record from the tuple data
        for number, name, rtype, floor, price, max_g in rooms:
            Room.objects.create(
                room_number=number, name=name, room_type=rtype,
                floor=floor, price_per_night=price, max_guests=max_g,
                status='vacant', is_clean=True,
            )
        self.stdout.write(f'Seeded {len(rooms)} rooms.')

    def _seed_packages(self):
        """Create the 12 pre-order packages across three categories."""
        packages = [
            ('welcome-champagne', 'Welcome Champagne & Strawberries', 'food', 45, '🥂',
             'Moet & Chandon on arrival with fresh strawberries and chocolate.'),
            ('breakfast-bed', 'Breakfast in Bed for Two', 'food', 65, '🍳',
             'Full Ember breakfast delivered to your room between 8am and 11am.'),
            ('ember-dinner', 'Ember Dinner Reservation', 'food', 185, '🍽️',
             'Table for two at Ember. Tasting menu included.'),
            ('minibar', 'Minibar Stocked to Preference', 'food', 95, '🥃',
             'Tell us your preferences and we will stock it before you arrive.'),
            ('celebration-cake', 'Celebration Cake', 'food', 55, '🎂',
             'Bespoke cake from the Ember kitchen.'),
            ('spa-signature', 'Obsidian Signature Massage', 'spa', 155, '💆',
             '90 minute deep tissue with heated obsidian stones.'),
            ('spa-morning', 'Morning Wellness — Pool & Yoga', 'spa', 85, '🧘',
             'Mineral pool, sauna, steam and rooftop yoga. Per person.'),
            ('spa-day', 'Full Spa Day', 'spa', 295, '✨',
             'All treatments, pool, thermal suite and lunch.'),
            ('honeymoon-package', 'Honeymoon Package', 'occasion', 195, '💍',
             'Flowers, champagne, rose petals, breakfast in bed.'),
            ('birthday-package', 'Birthday Package', 'occasion', 145, '🎁',
             'Cake, balloons, surprise champagne and dinner reservation.'),
            ('anniversary-package', 'Anniversary Package', 'occasion', 225, '💐',
             'Flowers, champagne, candles and dinner for two at Ember.'),
            ('proposal-package', 'Proposal Package', 'occasion', 495, '💎',
             'Location scouting, flowers, photographer, dinner reservation.'),
        ]
        # Create each package record from the tuple data
        for pid, name, cat, price, icon, desc in packages:
            Package.objects.create(
                package_id=pid, name=name, category=cat,
                price=price, icon=icon, description=desc, is_active=True,
            )
        self.stdout.write(f'Seeded {len(packages)} packages.')
