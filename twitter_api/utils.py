from functools import wraps
from hashlib import md5
from flask import request, g, abort
from datetime import datetime as dt
import json

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
        if 'access_token' not in request.json:
            abort(401)
        query = "SELECT a.user_id FROM auth a WHERE a.access_token=?;"
        c = g.db.execute(query, (request.json['access_token'],))
        user_id = c.fetchone()
        if not user_id:
            abort(401)
        kwargs['user_id'] = user_id[0]
        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.content_type != 'application/json':
            abort(400)
        return f(*args, **kwargs)
    return wrapper


def convert_time(d_t):
    return (dt.strptime(d_t,"%Y-%m-%d %H:%M:%S").strftime('%Y-%m-%dT%H:%M:%S'))