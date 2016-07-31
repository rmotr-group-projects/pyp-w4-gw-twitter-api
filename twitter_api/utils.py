from functools import wraps
from hashlib import md5


JSON_MIME_TYPE = 'application/json'


def hash_to_md5(string):
    return md5(string).hexdigest()
    

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
