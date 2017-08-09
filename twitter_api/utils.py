from functools import wraps
from hashlib import md5 as hashmd5

from flask import g, request, abort


JSON_MIME_TYPE = 'application/json'

def md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal 
    conversion of the token to bytes if run in Python 3
    """
    return hashmd5(token.encode('utf-8'))

def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        data = request.get_json()
        access_token = data.get('access_token', None)
        if access_token:
            cursor = g.db.execute("SELECT user_id FROM auth WHERE access_token=:access_token",
                                  {'access_token': access_token})
            user = cursor.fetchone()
            if user:
                kwargs['user_id'] = user[0]
            else:
                abort(401)
        else:
            abort(401)
        
        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        if request.content_type != 'application/json':
            abort(400)
        return f(*args, **kwargs)
    return decorated_function
