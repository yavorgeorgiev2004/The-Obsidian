"""
Concierge app — forms.
ConciergeRequestForm lets a guest submit a request with a preferred time.
It is a validated ModelForm that writes records to the database.
"""
from django import forms
from .models import ConciergeRequest


class ConciergeRequestForm(forms.ModelForm):
    """
    Form allowing a guest to submit a concierge request and a preferred
    time. Validates that the detail field carries enough information.
    """
    class Meta:
        model  = ConciergeRequest
        # The guest supplies a type, the detail, and their preferred time
        fields = ['request_type', 'detail', 'requested_time']
        widgets = {
            'request_type':   forms.Select(attrs={'class': 'form-control'}),
            'detail':         forms.Textarea(attrs={'class': 'form-control', 'rows': 5,
                                'placeholder': 'Tell us everything. No detail is too small...'}),
            'requested_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
        labels = {
            'requested_time': 'Preferred Date & Time',
        }

    def clean_detail(self):
        """Ensure the request detail is substantial enough to act on."""
        # Strip whitespace and require a minimum length
        detail = self.cleaned_data.get('detail', '').strip()
        if len(detail) < 10:
            raise forms.ValidationError('Please give us a little more detail about your request.')
        return detail
