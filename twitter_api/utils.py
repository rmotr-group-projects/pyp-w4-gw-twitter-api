from functools import wraps

import hashlib
import string
import random
from flask import request, g, abort

JSON_MIME_TYPE = 'application/json'

def md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal 
    conversion of the token to bytes if run in Python 3
    """
    return hashlib.md5(token.encode('utf-8'))


#taken from python docs
def make_token(size=12):
    token = string.ascii_letters + string.digits
    return ''.join(random.choice(token) for i in range(size))

def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            access_token = request.json['access_token']
        except KeyError: 
            abort (401)
        cursor = g.db.execute('SELECT user_id from auth where access_token=:access_token;', {'access_token':access_token})
        if not cursor.fetchone():
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
