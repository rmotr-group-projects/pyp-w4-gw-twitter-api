from functools import wraps
import hashlib
from flask import request, abort, g

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
        # implement your logic here
        if request.method =='GET':
            return f(*args, **kwargs)
        elif request.method in ['DELETE','POST']:
            if 'access_token' not in request.json:
                abort(401)
            return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.content_type != JSON_MIME_TYPE:
                abort(400)
        return f(*args, **kwargs)
    return decorated_function
