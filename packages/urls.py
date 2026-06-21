"""Packages app URL configuration."""
from django.urls import path
from . import views

app_name = 'packages'

urlpatterns = [
    path('', views.package_list, name='list'),
]
