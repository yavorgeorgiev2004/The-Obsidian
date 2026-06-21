"""
Forms for the complaints app.
ComplaintForm lets a guest raise a complaint with a category and detail,
optionally tied to one of their bookings.
"""
from django import forms
from .models import Complaint


class ComplaintForm(forms.ModelForm):
    """Form for a guest to submit a complaint."""

    class Meta:
        model  = Complaint
        fields = ['category', 'booking', 'detail']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'booking':  forms.Select(attrs={'class': 'form-control'}),
            'detail':   forms.Textarea(attrs={'class': 'form-control', 'rows': 5,
                          'placeholder': 'Please describe what went wrong...'}),
        }
        labels = {'booking': 'Related booking (optional)'}

    def __init__(self, *args, user=None, **kwargs):
        """Limit the booking choices to the submitting guest's own bookings."""
        super().__init__(*args, **kwargs)
        # Only the guest's own bookings can be attached to their complaint
        if user is not None:
            self.fields['booking'].queryset = user.bookings.all()
            self.fields['booking'].required = False

    def clean_detail(self):
        """Require enough detail to act on the complaint."""
        detail = self.cleaned_data.get('detail', '').strip()
        if len(detail) < 10:
            raise forms.ValidationError('Please give us a little more detail so we can help.')
        return detail
