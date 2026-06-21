"""Rooms admin configuration."""
from django.contrib import admin
from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display  = ['room_number', 'name', 'room_type', 'floor', 'price_per_night', 'status', 'is_clean']
    list_filter   = ['status', 'room_type', 'floor', 'is_clean']
    search_fields = ['room_number', 'name']
    list_editable = ['status', 'is_clean']
    ordering      = ['floor', 'room_number']
