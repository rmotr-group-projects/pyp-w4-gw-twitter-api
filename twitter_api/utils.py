from functools import wraps
import hashlib
from flask import (g, request)

JSON_MIME_TYPE = 'application/json'

def md5(token):
    '''
    Returns an md5 hash of a token passed as a string, performing an internal 
    conversion of the token to bytes if run in Python 3
    '''
    return hashlib.md5(token.encode('utf-8'))
    

def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        post = request.json
        if 'access_token' not in post:
            return '', 401
        
        user_present = """SELECT access_token FROM auth WHERE access_token=?"""
        result = g.db.execute(user_present, (post['access_token'],)).fetchone()
        if not result:
            return '', 401
        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.mimetype != JSON_MIME_TYPE:
            return '', 400
        return f(*args, **kwargs)
    return decorated_function