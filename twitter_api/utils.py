import sqlite3

from functools import wraps

from flask import Flask
from flask import request, make_response, jsonify, g
import string

from hashlib import md5

JSON_MIME_TYPE = 'application/json'

def md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal 
    conversion of the token to bytes if run in Python 3
    """
    pass

def valid_json_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.get_json() == None:
            return make_response(jsonify({'error': 'Request was not valid JSON. Bad request'}), 400)
        return f(*args, **kwargs)
    return decorated_function
    
    
def valid_token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in request.get_json():
            return make_response(jsonify({'error': 'No access_token was supplied. Unauthorised.'}), 401)
        # Now retrieve a list of all authorised users
        sql_string = '''
            SELECT
            access_token
            FROM
            auth;
        '''
        cursor = g.db.execute(sql_string)
        results = cursor.fetchall()
        if len(results) == 0:
            return make_response(jsonify({'error': 'Access token is invalid or has expired. Please log in again'}), 401)
        authorised = False;
        for result in results:
            if result[0] == request.json['access_token']:
                authorised = True;
                # Access token is present in 'auth' table. Proceed with function
        # Supplied access token not found in 'auth' table.
        if authorised:
            return f(*args, **kwargs)
        else:
            return make_response(jsonify({'error': 'Access token is invalid or has expired. Please log in again'}), 401)
    return decorated_function