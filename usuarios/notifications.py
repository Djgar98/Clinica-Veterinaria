from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification


def notify_users(users, title, message='', url='', level='info'):
    if not users:
        return []
    channel_layer = get_channel_layer()
    created = []
    for user in users:
        if not user:
            continue
        notif = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            url=url,
            level=level,
        )
        created.append(notif)
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}",
                {
                    'type': 'notify',
                    'id': notif.id,
                    'title': notif.title,
                    'message': notif.message,
                    'url': notif.url,
                    'level': notif.level,
                    'created_at': notif.created_at.isoformat(),
                }
            )
    return created
