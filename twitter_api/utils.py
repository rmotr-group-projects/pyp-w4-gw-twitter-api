from functools import wraps
from hashlib import md5
from flask import request, abort

JSON_MIME_TYPE = 'application/json'


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            abort(400)
        return f(*args, **kwargs)
    return decorated_function
