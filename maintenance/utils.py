"""
Helper logic for the maintenance app.

Small functions for summarising maintenance state, kept out of the views
so they can be reused and tested on their own.
"""
from .models import MaintenanceLog


def active_logs():
    """Return all active maintenance logs with their room preloaded."""
    # Preload the room to avoid a query per row when displaying the list
    return MaintenanceLog.objects.filter(status='active').select_related('room')


def escalation_counts():
    """
    Return a count of active maintenance logs at each urgency level, used
    for the dashboard badge so staff see at a glance what needs attention.
    Keys use underscores so they are accessible from Django templates.
    """
    # Tally each active log into its escalation bucket
    counts = {'upcoming': 0, 'due_soon': 0, 'overdue': 0}
    for log in active_logs():
        level = log.escalation()
        # Map the hyphenated escalation level to the underscore key
        key = level.replace('-', '_')
        if key in counts:
            counts[key] += 1
    return counts
