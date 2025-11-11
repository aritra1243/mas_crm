# process_team/context_processors.py
from authentication.models import Notification


def process_unread_count(request):
    """
    Context processor to add unread notification count to all templates
    for process team members.
    """
    if not request.user.is_authenticated:
        return {'process_unread_count': 0}
    
    # Only calculate for process team members
    if not hasattr(request.user, 'role') or request.user.role != 'process_team':
        return {'process_unread_count': 0}
    
    try:
        # Get all notifications and filter in Python to avoid Djongo NOT operator issue
        all_notifs = list(
            Notification.objects
            .filter(user=request.user)
            .only('id', 'is_read')
        )
        count = sum(1 for n in all_notifs if not getattr(n, 'is_read', False))
        return {'process_unread_count': count}
    except Exception:
        return {'process_unread_count': 0}