"""Admin registration for the relocations app."""
from django.contrib import admin
from .models import RelocationOffer


@admin.register(RelocationOffer)
class RelocationOfferAdmin(admin.ModelAdmin):
    """Admin list view for relocation offers and their status."""
    list_display  = ['__str__', 'guest', 'resolution', 'status', 'bonus_credit', 'created_at']
    list_filter   = ['resolution', 'status']
    search_fields = ['guest__email', 'booking__id']
    readonly_fields = ['created_at', 'resolved_at']
