"""Bookings app URL configuration."""
from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    # Dates-first booking flow: search dates -> gallery -> confirm
    path('',                              views.search,         name='search'),
    path('gallery/',                      views.gallery,        name='gallery'),
    path('create/',                       views.create_booking, name='create'),

    # Guest's own bookings list
    path('mine/',                         views.my_bookings,    name='my_bookings'),

    # JSON availability check used live by the edit page
    path('availability/',                 views.check_availability, name='availability'),

    # Re-enter checkout for an unpaid booking
    path('<int:booking_id>/pay/',         views.pay_deposit,    name='pay_deposit'),

    # Full edit of an existing booking
    path('<int:booking_id>/edit/',        views.edit_booking,   name='edit'),

    # Cancellation frees the dates for other guests
    path('<int:booking_id>/cancel/',      views.cancel_booking, name='cancel'),

    # Initial deposit payment and its success feedback
    path('<int:booking_id>/checkout/',    views.checkout,        name='checkout'),
    path('<int:booking_id>/success/',     views.payment_success, name='success'),

    # Top-up payment after an edit, and its success feedback
    path('<int:booking_id>/topup/',         views.topup,         name='topup'),
    path('<int:booking_id>/topup-success/', views.topup_success, name='topup_success'),

    # Shared failure feedback page
    path('<int:booking_id>/failure/',     views.payment_failure, name='failure'),

    # Stripe webhook endpoint
    path('webhook/',                      views.stripe_webhook, name='webhook'),
]
