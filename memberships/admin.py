"""Admin registration for the memberships app."""
from django.contrib import admin
from .models import Membership


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin view of memberships and their validity."""
    list_display  = ['member', 'tier', 'started_at', 'expires_at']
    list_filter   = ['tier']
    search_fields = ['member__email']
