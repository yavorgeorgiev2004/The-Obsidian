"""Concierge app URL configuration."""
from django.urls import path
from . import views

app_name = 'concierge'

urlpatterns = [
    # Guest creates and tracks requests
    path('',                            views.create_request,      name='create'),
    path('mine/',                       views.my_requests,         name='my_requests'),

    # Guest responds to a staff-proposed time (confirm or counter)
    path('<int:request_id>/respond/',   views.respond_to_proposal, name='respond'),

    # Staff manage a request (accept, propose, complete)
    path('<int:request_id>/manage/',    views.manage_request,      name='manage'),
]
