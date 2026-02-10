import threading

_locals = threading.local()


def set_current_request(request):
    _locals.request = request


def get_current_request():
    return getattr(_locals, 'request', None)


def get_current_user():
    req = get_current_request()
    if not req:
        return None
    user = getattr(req, 'user', None)
    if user and user.is_authenticated:
        return user
    return None
