from functools import wraps
from flask import Flask, Response, request, abort
from flask import g
from hashlib import md5 # because the test is importing from here...

JSON_MIME_TYPE = 'application/json'


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        
        # this is used if they are doing a POST request
        # check the json of the request to get the access token
        # then see if that access token exists in the auth table
        client_data = request.get_json()
        try:
            post_access_token = client_data['access_token']
        except KeyError:
            abort(401)
        
        sql_command = 'SELECT 1 FROM auth WHERE access_token = ?'
        sql_result = g.db.execute(sql_command, [post_access_token])
        sql_value = sql_result.fetchone()
        if not sql_value:
            abort(401) # not authorized
        
        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # implement your logic here
        
        # check if POST request is mimetype of application/json
        # get_json returns None if not json
        if request.get_json() is None:
            abort(400) # Bad request
            
        return f(*args, **kwargs)
    return decorated_function
