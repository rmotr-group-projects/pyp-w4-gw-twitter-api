from functools import wraps
from hashlib import md5 as python_md5
from flask import g, request

JSON_MIME_TYPE = 'application/json'

def md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal 
    conversion of the token to bytes if run in Python 3
    """
    token = token.encode('utf-8')
    return python_md5(token)


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        data = request.get_json()
        if 'access_token' not in data:
            return 'Access token missing', 401
        token = data['access_token']
        #print(token)
        token_fetch = g.db.execute('select access_token from auth').fetchall()
        tokens =[x[0] for x in token_fetch]
        
        #print(tokens)
        if token not in tokens:
            return 'Incorrect token', 401
        return f(*args, **kwargs)
    return decorated_function

def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        print(request.content_type)
        if not request.is_json:
            return '', 400
        return f(*args, **kwargs)
    return decorated_function


