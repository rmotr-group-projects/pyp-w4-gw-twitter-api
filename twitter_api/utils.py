from functools import wraps
from flask import g, request, abort
from hashlib import md5

JSON_MIME_TYPE = 'application/json'


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verify that json is supplied in the request
        if request.json is None:
            abort(400)
        
        # Verify that an access token was given
        if 'access_token' not in request.json:
            abort(401)
        
        # Verify that the access token is in the auth table
        query = 'SELECT COUNT(*) FROM auth WHERE access_token=?;'
        cursor = g.db.execute(query, (request.json['access_token'],))
        count = cursor.fetchone()[0]
        if not count:
            abort(401)
        
        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verify that json is supplied in the request
        if request.json is None:
            abort(400)
        
        return f(*args, **kwargs)
    return decorated_function
