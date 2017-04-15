from functools import wraps
from hashlib import md5

JSON_MIME_TYPE = 'application/json'

def _md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal 
    conversion of the token to bytes if run in Python 3
    """
    return md5(token.encode('utf-8')).hexdigest()

def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # is user
        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            json.loads(args, kwargs)
        except ValueError:
            return 
        return f(*args, **kwargs)
    return decorated_function
