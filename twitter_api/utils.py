from functools import wraps
from flask import abort

JSON_MIME_TYPE = 'application/json'


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        userdata = request.get_json()
        token = userdata['access_token']
        lookup = g.db.execute('SELECT 1 FROM auth WHERE access_token = ?', (token,))
        if not lookup.fetchone():
            abort(401)
        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.get_json() is None:
            abort(400)
        return f(*args, **kwargs)
    return decorated_function

