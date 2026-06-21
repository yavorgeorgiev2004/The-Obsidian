"""
The Obsidian Hotel Platform — Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/',          admin.site.urls),
    path('',                include('core.urls')),
    path('accounts/',       include('allauth.urls')),
    path('accounts/',       include('accounts.urls')),
    path('rooms/',          include('rooms.urls')),
    path('bookings/',       include('bookings.urls')),
    path('packages/',       include('packages.urls')),
    path('concierge/',      include('concierge.urls')),
    path('dashboard/',      include('dashboard.urls')),
    path('relocations/',    include('relocations.urls')),
    path('maintenance/',    include('maintenance.urls')),
    path('complaints/',     include('complaints.urls')),
    path('membership/',     include('memberships.urls')),
]

# Serve static and media files.
# Explicitly routing /static/ ensures the stylesheet and scripts load
# during local development even if DEBUG is turned off.
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
