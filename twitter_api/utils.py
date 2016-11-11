from functools import wraps
from hashlib import md5 as md5lib
from flask import abort, session, redirect, url_for, request, g
import uuid


JSON_MIME_TYPE = 'application/json'

def md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal 
    conversion of the token to bytes if run in Python 3
    """
    hashed = md5lib(str(token))
    return hashed

def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in request.json:
            abort(401)
            
        cursor = g.db.execute("SELECT * FROM auth WHERE access_token=?",(request.json['access_token'],))
        if cursor.fetchone() == None:
            abort(401)
        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.content_type != JSON_MIME_TYPE:
            abort(400)
        return f(*args, **kwargs)
    return decorated_function

def make_uid():
    uid = uuid.uuid4()
    return str(uid)