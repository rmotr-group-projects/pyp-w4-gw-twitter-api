from functools import wraps
from flask import Flask, Response, request, abort, g
from hashlib import md5

JSON_MIME_TYPE = 'application/json'


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        # if token != token from database
        
        # check that we even got a access_token at all
        if 'access_token' not in request.json:
            abort(401)
        
        query = 'SELECT * FROM auth WHERE access_token=?'
        cursor = g.db.execute(query, ([request.json['access_token']]))
        count = cursor.fetchone()[0]
        if not count: #if access_token doesn't match one in db, throw 401
            abort(401)

        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        if request.json is None: #Verify Json in, else abort & throw 400
            abort(400)
        return f(*args, **kwargs)
    return decorated_function
