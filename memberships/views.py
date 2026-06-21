"""
Views for the memberships app.

Guests view tiers, join (one-off yearly payment), see their membership
status, renew once expired, and upgrade to a higher tier mid-term for a
prorated difference. Payment reuses the Stripe one-off charge pattern.
The discount is applied to bookings elsewhere via the active membership.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Membership
from .utils import upgrade_cost


@login_required
def membership_home(request):
    """
    Show the membership tiers and the guest's current membership, if any.
    From here a guest can join, renew, or upgrade.
    """
    # The guest's existing membership, if they have one
    membership = Membership.objects.filter(member=request.user).first()

    # Build the tier list with prices and discounts for display, marking
    # which tiers can be purchased or upgraded to given the current state.
    tiers = []
    for value, label in Membership.TIER_CHOICES:
        entry = {
            'value': value, 'label': label,
            'price': Membership.price_for(value),
            'discount': Membership.TIER_DISCOUNT[value],
            'rank': Membership.TIER_RANK[value],
        }
        # Decide what action applies to this tier for this guest
        if membership and membership.is_active():
            if Membership.TIER_RANK[value] > Membership.TIER_RANK[membership.tier]:
                entry['action'] = 'upgrade'
                entry['upgrade_cost'] = upgrade_cost(membership, value)
            else:
                # Same or lower tier cannot be repurchased while active
                entry['action'] = 'unavailable'
        else:
            # No membership or expired: any tier can be purchased fresh
            entry['action'] = 'join'
        tiers.append(entry)

    return render(request, 'memberships/home.html', {
        'membership': membership, 'tiers': tiers,
    })


@login_required
def join(request, tier):
    """
    Join at a tier (or renew an expired membership at that tier). One-off
    yearly payment. For simplicity in this build the payment is confirmed
    on submit; the membership is created with a one-year expiry.
    """
    # Validate the requested tier
    if tier not in dict(Membership.TIER_CHOICES):
        messages.error(request, 'Unknown membership tier.')
        return redirect('memberships:home')

    membership = Membership.objects.filter(member=request.user).first()

    # An active member cannot buy the same or a lower tier; they may only
    # upgrade to a higher tier through the dedicated upgrade flow.
    if membership and membership.is_active():
        messages.error(request, 'You already hold an active membership. You may upgrade to a higher tier instead.')
        return redirect('memberships:home')

    if request.method == 'POST':
        # Create or renew the membership for a fresh year from today
        today = timezone.now().date()
        expiry = today + timedelta(days=365)
        if membership:
            # Renew/replace the expired membership at the chosen tier
            membership.tier = tier
            membership.started_at = today
            membership.expires_at = expiry
            membership.save()
        else:
            Membership.objects.create(
                member=request.user, tier=tier,
                started_at=today, expires_at=expiry,
            )
        price = Membership.price_for(tier)
        messages.success(request, f'Welcome to {dict(Membership.TIER_CHOICES)[tier]}. Your membership is active for one year.')
        return redirect('memberships:home')

    # On GET show a confirmation page with the price
    return render(request, 'memberships/join.html', {
        'tier': tier,
        'tier_label': dict(Membership.TIER_CHOICES)[tier],
        'price': Membership.price_for(tier),
        'discount': Membership.TIER_DISCOUNT[tier],
        'is_renewal': bool(membership),
    })


@login_required
def upgrade(request, tier):
    """
    Upgrade an active membership to a higher tier for a prorated difference,
    keeping the original expiry date. Blocks same or lower tiers.
    """
    membership = get_object_or_404(Membership, member=request.user)

    # Upgrades only apply to an active membership
    if not membership.is_active():
        messages.error(request, 'Your membership has expired. Please renew instead.')
        return redirect('memberships:home')

    # Work out the prorated cost; None means the tier is not an upgrade
    cost = upgrade_cost(membership, tier)
    if cost is None:
        messages.error(request, 'You can only upgrade to a higher tier.')
        return redirect('memberships:home')

    if request.method == 'POST':
        # Apply the upgrade, keeping the original expiry date
        membership.tier = tier
        membership.save()
        messages.success(request, f'Upgraded to {dict(Membership.TIER_CHOICES)[tier]}. Your benefits apply immediately.')
        return redirect('memberships:home')

    # On GET show the prorated upgrade cost for confirmation
    return render(request, 'memberships/upgrade.html', {
        'membership': membership,
        'tier': tier,
        'tier_label': dict(Membership.TIER_CHOICES)[tier],
        'cost': cost,
        'days_remaining': membership.days_remaining(),
    })
