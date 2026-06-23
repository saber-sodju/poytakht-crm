def unread_notifications(request):
    if request.user.is_authenticated and hasattr(request.user, 'notifications'):
        count = request.user.notifications.filter(is_read=False).count()
        recent = request.user.notifications.filter(is_read=False)[:5]
        return {'unread_count': count, 'recent_notifications': recent}
    return {'unread_count': 0, 'recent_notifications': []}
