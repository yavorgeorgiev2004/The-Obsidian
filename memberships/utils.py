"""
Helper logic for the memberships app.

upgrade_cost computes the prorated price to move an active membership to a
higher tier: the annual price difference, scaled by the fraction of the
year remaining, rounded up to the nearest whole pound with a minimum of £1.
"""
from decimal import Decimal
from math import ceil
from .models import Membership


def upgrade_cost(membership, new_tier):
    """
    Return the prorated cost to upgrade an active membership to new_tier.

    The charge is the annual price difference between the tiers multiplied
    by the share of the year still remaining, rounded up to the nearest
    whole pound and never less than one pound. Returns None when new_tier is
    not actually a higher tier than the current one.
    """
    # Only a strictly higher tier can be upgraded to
    current_rank = Membership.TIER_RANK.get(membership.tier, 0)
    new_rank = Membership.TIER_RANK.get(new_tier, 0)
    if new_rank <= current_rank:
        return None

    # The annual price gap between the two tiers
    annual_gap = Membership.price_for(new_tier) - Membership.price_for(membership.tier)

    # The fraction of the year still remaining (days left over 365)
    days_left = membership.days_remaining()
    fraction = Decimal(days_left) / Decimal(365)

    # Prorate, round up to the nearest whole pound, and floor at £1
    raw = annual_gap * fraction
    pounds = ceil(raw)
    return max(pounds, 1)
