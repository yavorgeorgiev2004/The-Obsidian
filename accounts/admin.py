"""Accounts admin configuration."""
from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'role', 'loyalty_tier', 'loyalty_points', 'created_at']
    list_filter   = ['role', 'loyalty_tier']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    list_editable = ['role']
