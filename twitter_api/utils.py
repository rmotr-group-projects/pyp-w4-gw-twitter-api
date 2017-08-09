from functools import wraps
import hashlib
from flask import g, redirect, request, url_for, abort

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
        data = request.get_json()
        if 'access_token' not in data:
            abort(401)
        cursor = g.db.execute(
            'SELECT access_token FROM auth WHERE access_token=:access_token;',
            {'access_token': data['access_token']})
        token = cursor.fetchone()
        if token is None:
            abort(401)
        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers['Content-Type'] !='application/json':
            abort(400)
        return f(*args, **kwargs)
    return decorated_function
