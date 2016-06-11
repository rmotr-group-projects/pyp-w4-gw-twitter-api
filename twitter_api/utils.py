from functools import wraps
from hashlib import md5

JSON_MIME_TYPE = 'application/json'


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        # if no token, return 401 
        # if token is wrong, return 401
        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    # if json, return the function
    # if not json, return 400
    def decorated_function(*args, **kwargs):
        # implement your logic here
        
        return f(*args, **kwargs)
    return decorated_function


#def md5(string_to_hash):
#    return md5(string_to_hash).hexdigest()