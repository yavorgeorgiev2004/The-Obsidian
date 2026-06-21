"""Admin registration for the complaints app."""
from django.contrib import admin
from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    """Admin view of complaints and their handling state."""
    list_display  = ['guest', 'category', 'status', 'handled_by', 'credit_awarded', 'created_at']
    list_filter   = ['status', 'category']
    search_fields = ['guest__email', 'detail']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at']
