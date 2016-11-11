from functools import wraps
from flask import request, abort, g
import hashlib

JSON_MIME_TYPE = 'application/json'

def md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal 
    conversion of the token to bytes if run in Python 3
    """
    
    if type(token) != bytes:
        token = token.encode('utf-8')
    
    token = hashlib.md5(token)
    
    return token


def query_db(query, args=(), one=False):
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        data = request.get_json()
        if data is None:
            abort(400)
        token = data.get('access_token', None)
        if token is None:
            abort(401)
        
        user_id = query_db('SELECT user_id FROM auth WHERE access_token = ?', [token], one=True)
        
        if not user_id:
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
