import json

from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict

from .models import AuditLog
from .threadlocals import get_current_user, get_current_request
from .security import get_client_ip


def compute_changes(instance, old_instance=None):
    if not old_instance:
        return {}
    new_data = model_to_dict(instance)
    old_data = model_to_dict(old_instance)
    changes = {}
    for key, new_val in new_data.items():
        old_val = old_data.get(key)
        if new_val != old_val:
            changes[key] = {'old': old_val, 'new': new_val}
    return changes


def log_action(instance, action, changes=None):
    request = get_current_request()
    user = get_current_user()
    try:
        ct = ContentType.objects.get_for_model(instance.__class__)
    except Exception:
        ct = None
    # Ensure JSON-serializable values (e.g., Decimal) for JSONField.
    safe_changes = json.loads(json.dumps(changes or {}, default=str))
    AuditLog.objects.create(
        user=user,
        content_type=ct,
        object_id=str(getattr(instance, 'pk', '')),
        model_label=f"{instance.__class__._meta.app_label}.{instance.__class__._meta.model_name}",
        action=action,
        changes=safe_changes,
        ip_address=get_client_ip(request),
        user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:300] if request else '',
    )
