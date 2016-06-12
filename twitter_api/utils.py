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
    
def has_json_keys(*keys, **kwargs):
    # same as has_json_keys(*keys, error = 401) but works with python 2
    error = kwargs.pop('error', 401)
    def outer(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            for json_key in keys:
                if json_key not in request.json:
                    abort(error)
            return f(*args, **kwargs)
        return decorated_function
    return outer
        
