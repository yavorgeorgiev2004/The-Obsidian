"""URL configuration for the memberships app."""
from django.urls import path
from . import views

app_name = 'memberships'

urlpatterns = [
    # Tiers and current membership
    path('',                    views.membership_home, name='home'),
    # Join or renew at a tier
    path('join/<str:tier>/',    views.join,            name='join'),
    # Upgrade an active membership to a higher tier
    path('upgrade/<str:tier>/', views.upgrade,         name='upgrade'),
]
