"""Admin registration for the maintenance app."""
from django.contrib import admin
from .models import MaintenanceLog, StaffActionLog


@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    """Admin view of maintenance events and their windows."""
    list_display  = ['room', 'category', 'status', 'started', 'expected_ready', 'created_by', 'cleared_by']
    list_filter   = ['status', 'category']
    search_fields = ['room__room_number']
    readonly_fields = ['created_at', 'cleared_at']


@admin.register(StaffActionLog)
class StaffActionLogAdmin(admin.ModelAdmin):
    """Admin view of the staff action audit trail."""
    list_display  = ['staff', 'action', 'detail', 'created_at']
    list_filter   = ['action']
    search_fields = ['staff__email', 'detail']
    readonly_fields = ['created_at']
