"""
Bookings app — models.
Core e-commerce models linking guests, rooms and packages, with full
payment tracking (total, deposit, amount paid, balance owed) so that
guests, receptionists and managers can all see the financial state of
any booking.
"""
from django.db import models
from django.contrib.auth.models import User
from rooms.models import Room
from packages.models import Package


class Booking(models.Model):
    """
    Represents a single hotel booking and its full payment state.
    Availability across the platform is derived from these records:
    a room is taken for a date range only if an active (non-cancelled)
    booking overlaps that range. Cancelling or editing a booking
    therefore frees its dates for other guests automatically.
    """

    # The lifecycle states a booking moves through
    STATUS_CHOICES = [
        ('pending-payment', 'Pending Payment'),  # created but deposit not yet paid
        ('confirmed',    'Confirmed'),
        ('due-in',       'Due In'),
        ('checked-in',   'Checked In'),
        ('checked-out',  'Checked Out'),
        ('cancelled',    'Cancelled'),
        ('superseded',   'Superseded'),  # replaced by an edited booking
    ]

    # Who booked, which room, and the packages attached to the stay
    guest            = models.ForeignKey(User, on_delete=models.PROTECT, related_name='bookings')
    room             = models.ForeignKey(Room, on_delete=models.PROTECT, related_name='bookings')
    packages         = models.ManyToManyField(Package, through='BookingPackage', blank=True)

    # The dates and party size for this stay
    check_in         = models.DateField()
    check_out        = models.DateField()
    guests_count     = models.PositiveSmallIntegerField(default=1)

    # Current lifecycle status and any free-text guest requests
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    special_requests = models.TextField(blank=True)

    # ── Money fields — the single source of truth for payment state ──
    # room_total + packages_total = grand_total
    # amount_paid tracks everything actually paid (deposit + top-ups)
    # balance_owed is what remains to pay at the hotel
    room_total       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    packages_total   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    membership_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_owed     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deposit_paid     = models.BooleanField(default=False)

    # Stripe reference for the most recent payment intent on this booking
    stripe_payment_intent = models.CharField(max_length=200, blank=True)

    # Timestamps for record keeping
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-check_in']
        verbose_name        = 'Booking'
        verbose_name_plural = 'Bookings'

    def __str__(self):
        return f'BK{self.pk:04d} — {self.guest.get_full_name()} — Room {self.room.room_number}'

    def nights(self):
        """Return the number of nights between check-in and check-out."""
        return (self.check_out - self.check_in).days

    def calculate_totals(self):
        """
        Recalculate every money figure from the current room, nights and
        packages. Called whenever the booking is created or edited so the
        totals always reflect the latest details. Returns any overpayment
        (amount paid above the grand total) so the caller can move it to
        the guest's credit balance.
        """
        # Room cost is the nightly rate times the number of nights
        self.room_total = self.room.price_per_night * self.nights()

        # Apply any active membership discount the guest holds to the room
        # rate. The discount only applies while the membership is active; an
        # expired membership reduces nothing. Stored so it can be shown.
        self.membership_discount = 0
        membership = getattr(self.guest, 'membership', None)
        if membership is not None:
            percent = membership.discount_percent()
            if percent:
                from decimal import Decimal
                discount = (self.room_total * Decimal(percent) / Decimal(100))
                self.membership_discount = round(discount, 2)
                self.room_total = self.room_total - self.membership_discount

        # Packages cost is the sum of each attached package's stored price
        self.packages_total = sum(
            bp.price_at_booking for bp in self.bookingpackage_set.all()
        )

        # The grand total is simply the two combined
        self.grand_total = self.room_total + self.packages_total

        # Work out any overpayment: money paid above the new grand total
        overpayment = 0
        if self.amount_paid > self.grand_total:
            overpayment = self.amount_paid - self.grand_total

        # The balance owed is the grand total minus whatever has been paid,
        # but never below zero — an overpaid booking owes nothing.
        self.balance_owed = max(self.grand_total - self.amount_paid, 0)
        return overpayment

    def is_fully_deposited(self):
        """Return True when enough has been paid to cover the deposit."""
        # Compares the amount paid against the required deposit figure
        return self.amount_paid >= self.deposit_amount()

    def is_fully_paid(self):
        """Return True when the whole grand total has been paid."""
        # Nothing is owed once the amount paid reaches the grand total
        return self.amount_paid >= self.grand_total

    def amount_due_now(self):
        """
        Return the amount the guest must pay now to secure the booking.
        This is the deposit minus whatever has already been paid, never
        less than zero. When credit or earlier payment already covers the
        deposit, this is zero and no card payment is needed.
        """
        # The shortfall between the required deposit and what is paid
        return max(self.deposit_amount() - self.amount_paid, 0)

    def needs_payment(self):
        """Return True when there is still a deposit amount to collect."""
        # A payment is only needed when something is genuinely due now
        return self.amount_due_now() > 0

    def deposit_amount(self):
        """Return the 25% deposit figure for the current grand total."""
        return round(self.grand_total * 25 / 100, 2)

    def top_up_due(self):
        """
        Work out how much more must be paid now to bring the amount paid
        up to the required deposit. Used when a guest edits a booking
        upward. Returns zero if no extra deposit is owed.
        """
        required = self.deposit_amount()
        # Only charge a top-up if the deposit due exceeds what is paid
        if required > self.amount_paid:
            return round(required - self.amount_paid, 2)
        return 0

    def apply_payment(self, amount):
        """
        Record a payment against the booking. Increases amount paid,
        recalculates the balance, and flags the deposit as met once the
        amount paid reaches the deposit figure.
        """
        # Add the new payment to the running paid total
        self.amount_paid += amount

        # Recalculate the outstanding balance after the payment,
        # never letting it fall below zero
        self.balance_owed = max(self.grand_total - self.amount_paid, 0)

        # Mark the deposit as satisfied once enough has been paid
        if self.amount_paid >= self.deposit_amount():
            self.deposit_paid = True
        self.save()


class BookingPackage(models.Model):
    """
    Through model for the Booking-to-Package many-to-many relationship.
    Stores the package price at the moment of booking, so later price
    changes to a Package never alter an existing booking's total.
    """
    booking          = models.ForeignKey(Booking, on_delete=models.CASCADE)
    package          = models.ForeignKey(Package, on_delete=models.PROTECT)
    price_at_booking = models.DecimalField(max_digits=8, decimal_places=2)
    added_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('booking', 'package')
        verbose_name        = 'Booking Package'
        verbose_name_plural = 'Booking Packages'

    def __str__(self):
        return f'{self.booking} + {self.package.name}'
