from functools import wraps
from hashlib import md5
from flask import request, abort

JSON_MIME_TYPE = 'application/json'

# Checks request token
def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        return f(*args, **kwargs)
    return decorated_function

# Make sure content is suppose to be JSON
def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.content_type != JSON_MIME_TYPE:
            abort(400)
        return f(*args, **kwargs)
    return decorated_function
