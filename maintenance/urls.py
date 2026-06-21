"""URL configuration for the maintenance app."""
from django.urls import path
from . import views

app_name = 'maintenance'

urlpatterns = [
    # The maintenance board (tab) listing active maintenance
    path('',                      views.maintenance_board,  name='board'),

    # Set, extend and clear maintenance on a room
    path('room/<int:room_id>/set/',    views.set_maintenance,    name='set'),
    path('log/<int:log_id>/extend/',   views.extend_maintenance, name='extend'),
    path('log/<int:log_id>/clear/',    views.clear_maintenance,  name='clear'),

    # Manager-only full audit trail of staff actions
    path('audit/',                views.audit_log,          name='audit'),
]
