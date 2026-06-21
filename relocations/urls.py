"""URL configuration for the relocations app."""
from django.urls import path
from . import views

app_name = 'relocations'

urlpatterns = [
    # Staff confirm maintenance on a room that has bookings
    path('maintenance/<int:room_id>/confirm/', views.confirm_maintenance, name='confirm_maintenance'),

    # Guest decides how to handle their disrupted booking
    path('offer/<int:offer_id>/decide/',       views.guest_decision,      name='decide'),

    # Staff record a decision a guest gave by phone or in person
    path('offer/<int:offer_id>/record/',       views.staff_record_decision, name='staff_record'),
]
