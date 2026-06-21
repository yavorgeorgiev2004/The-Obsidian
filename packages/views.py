"""
Packages app — views.
Read-only listing of available pre-order packages, grouped by category.
"""
from django.shortcuts import render
from .models import Package


def package_list(request):
    """Display all active packages grouped by their category."""
    # Fetch only packages currently marked active
    packages = Package.objects.filter(is_active=True)

    # Group packages by category for tidy template rendering
    grouped = {}
    for pkg in packages:
        grouped.setdefault(pkg.category, []).append(pkg)

    return render(request, 'packages/list.html', {
        'grouped': grouped,
        # Logged-in guests get the portal shell; visitors get the public site.
        'base_template': 'portal_base.html' if request.user.is_authenticated else 'base.html',
    })
