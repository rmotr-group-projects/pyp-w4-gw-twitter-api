from functools import wraps
from flask import request, abort
import hashlib

JSON_MIME_TYPE = 'application/json'

def md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal 
    conversion of the token to bytes if run in Python 3
    """
    return hashlib.md5(token.encode('utf-8'))

def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        request_dict = request.get_json()
        access_token = request_dict.get('access_token', None)
        if access_token:
            return f(*args, **kwargs)
        else:
            abort(401)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.content_type == JSON_MIME_TYPE:
            return f(*args, **kwargs)
        else:
            abort(400)
    return decorated_function
