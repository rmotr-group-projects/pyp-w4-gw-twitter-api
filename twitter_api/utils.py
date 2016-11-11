import hashlib
import uuid
from functools import wraps

from flask import abort, request

JSON_MIME_TYPE = 'application/json'


def md5(token):
    if type(token) != bytes:
        token = token.encode('utf-8')
    return hashlib.md5(token)


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.get_json() and "access_token" not in request.get_json():
            abort(401)
        return f(*args, **kwargs)

    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            abort(400)
        return f(*args, **kwargs)

    return decorated_function


def create_token():
    token = str(uuid.uuid1())[9:]
    return token
