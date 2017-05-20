from functools import wraps
import hashlib
from flask import request, abort

JSON_MIME_TYPE = 'application/json'

def md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal 
    conversion of the token to bytes if run in Python 3
    """
    m = hashlib.md5()
    m.update(token.encode('utf-8'))
    return m #if it wants a raw binary instead of a hexadecimal string, use digest()

def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json()
        if data is None:
            return abort(400)
        return f(*args, data=data, **kwargs)
    return decorated_function

def auth_only(data):
    def arg_nest(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            access_token = data['access_token']
            
            #verify that access_token is registered to db
            cursor = g.db.execute('SELECT id FROM auth WHERE access_token=?', [access_token]) #moves cursor to auth record matching access_token
            account_result = cursor.fetchone()
            if account_result is None:
                return abort(401)
            account_id = account_result[0]
            
            return f(*args, data=data, authorized_user_id=account_id, **kwargs)
        return decorated_function
    return arg_nest

