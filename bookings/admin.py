"""Bookings admin configuration."""
from django.contrib import admin
from .models import Booking, BookingPackage


class BookingPackageInline(admin.TabularInline):
    """Inline editor for packages attached to a booking."""
    model  = BookingPackage
    extra  = 0
    readonly_fields = ['price_at_booking']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Admin view showing the full payment state of each booking."""
    list_display  = ['__str__', 'check_in', 'check_out', 'status',
                     'grand_total', 'amount_paid', 'balance_owed', 'deposit_paid']
    list_filter   = ['status', 'check_in', 'deposit_paid']
    search_fields = ['guest__email', 'guest__first_name', 'guest__last_name', 'room__room_number']
    inlines       = [BookingPackageInline]
    readonly_fields = ['grand_total', 'room_total', 'packages_total',
                       'balance_owed', 'created_at', 'updated_at']
