"""
In-app notifications to management.

Anything destructive or financially significant done by staff should surface
to the people responsible for the business — the director and the admin —
without them having to go read the audit log. The audit log is the permanent
record; these are the nudge.
"""
import logging

logger = logging.getLogger('apps.accounts')


def notify_management(*, notification_type, title, message='', link='', exclude_user=None):
    """
    Create a Notification for every active director and admin.

    Never raises: a notification failure must not roll back the action it is
    reporting on (same rule as audit logging).
    """
    from .models import CustomUser, Notification

    try:
        recipients = CustomUser.objects.filter(
            role__in=(CustomUser.ROLE_DIRECTOR, CustomUser.ROLE_ADMIN),
            is_active=True,
        )
        if exclude_user is not None and exclude_user.pk:
            recipients = recipients.exclude(pk=exclude_user.pk)

        Notification.objects.bulk_create([
            Notification(
                user=person,
                notification_type=notification_type,
                title=title[:200],
                message=message,
                link=link,
            )
            for person in recipients
        ])
    except Exception as exc:                # pragma: no cover
        logger.error('Failed to notify management: %s', exc, exc_info=True)
