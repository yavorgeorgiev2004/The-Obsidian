"""dashboard app URL configuration."""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('',           views.home,               name='home'),
    path('guest/',     views.guest_dashboard,    name='guest'),
    path('reception/', views.reception_dashboard,name='reception'),
    path('manager/',   views.manager_dashboard,  name='manager'),

    # Staff room-management actions (POST only, role-protected)
    path('booking/<int:booking_id>/check-in/',  views.check_in_booking,   name='check_in'),
    path('booking/<int:booking_id>/check-out/', views.check_out_booking,  name='check_out'),
    path('room/<int:room_id>/toggle-clean/',    views.toggle_clean,       name='toggle_clean'),
    path('room/<int:room_id>/toggle-maintenance/', views.toggle_maintenance, name='toggle_maintenance'),
]
