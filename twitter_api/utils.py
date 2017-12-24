import hashlib
from functools import wraps

JSON_MIME_TYPE = 'application/json'


def md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal
    conversion of the token to bytes if run in Python 3

    What is going on here ???
    """
    new_token = token
    if str != bytes:
        new_token = token.encode('utf-8')
    return hashlib.md5(new_token)


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        return f(*args, **kwargs)
    return decorated_function
