"""
Bookings app — forms.
Contains the BookingForm: a ModelForm with custom validation that lets
guests create Booking records. This satisfies the requirement for a
validated form that writes to the database (beyond authentication).
"""
from django import forms
from django.utils import timezone
from .models import Booking


class BookingForm(forms.ModelForm):
    """
    Form for creating and editing a booking.
    Validates the date range and guest count before allowing a save.
    """
    class Meta:
        model  = Booking
        fields = ['room', 'check_in', 'check_out', 'guests_count', 'special_requests']
        widgets = {
            'check_in':         forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_out':        forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'guests_count':     forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'special_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'room':             forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        """
        Validate the whole form. Checks that the dates make sense and
        that the requested guest count does not exceed the room capacity.
        """
        cleaned = super().clean()
        check_in     = cleaned.get('check_in')
        check_out    = cleaned.get('check_out')
        guests_count = cleaned.get('guests_count')
        room         = cleaned.get('room')

        # Both dates are required to run any date validation
        if check_in and check_out:
            # Check-in cannot be in the past
            if check_in < timezone.now().date():
                self.add_error('check_in', 'Check-in date cannot be in the past.')

            # Check-out must come strictly after check-in
            if check_out <= check_in:
                self.add_error('check_out', 'Check-out must be after check-in.')

        # Guest count cannot exceed the chosen room's maximum capacity
        if room and guests_count:
            if guests_count > room.max_guests:
                self.add_error(
                    'guests_count',
                    f'This room holds a maximum of {room.max_guests} guests.'
                )

        return cleaned
