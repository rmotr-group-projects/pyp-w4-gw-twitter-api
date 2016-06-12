from functools import wraps
from hashlib import md5
from flask import g, request, abort
import json

JSON_MIME_TYPE = 'application/json'


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = json.loads(request.data)
        try: #Try to get the access token
            token = data["access_token"]
        except: #If it wasnt passed, throw a 401
            return abort(401)
        
        #If it was passed, query to check if it's valid   
        query = "SELECT user_id FROM auth WHERE access_token = ?"
        cursor = g.db.execute(query, (token, ))
        user = cursor.fetchone()
        if not user: #If it's not valid, throw a 401
            abort(401)
        return f(*args, **kwargs)
    return decorated_function
    

def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            data = json.loads(request.data)
        except:
            return abort(400)
        else:
            return f(*args, **kwargs)
    return decorated_function

