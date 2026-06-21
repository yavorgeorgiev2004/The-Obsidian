"""URL configuration for the complaints app."""
from django.urls import path
from . import views

app_name = 'complaints'

urlpatterns = [
    # Guest raises and tracks complaints
    path('',                          views.create_complaint, name='create'),
    path('mine/',                     views.my_complaints,    name='my_complaints'),

    # Staff queue and per-complaint management
    path('queue/',                    views.complaint_queue,  name='queue'),
    path('<int:complaint_id>/manage/', views.manage_complaint, name='manage'),
]
