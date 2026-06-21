"""Concierge admin configuration."""
from django.contrib import admin
from .models import ConciergeRequest


@admin.register(ConciergeRequest)
class ConciergeRequestAdmin(admin.ModelAdmin):
    """Admin view for concierge requests and their negotiation state."""
    list_display  = ['guest', 'request_type', 'status', 'requested_time', 'created_at']
    list_filter   = ['status', 'request_type']
    search_fields = ['guest__email', 'detail']
    readonly_fields = ['created_at', 'updated_at']
