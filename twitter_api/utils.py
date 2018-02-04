"""
This module contains some utility functions for use in main.py.
"""

from functools import wraps
from datetime import datetime
from flask import make_response, request, abort, g
import json
import sqlite3
import hashlib
import random
import string

JSON_MIME_TYPE = 'application/json'

def md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal 
    conversion of the token to bytes if run in Python 3
    """
    return hashlib.md5(token.encode('utf-8'))

def auth_only(f):
    """Decorator that checks for an authorized user based on their access token."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in request.json:
            abort(401)
        
        query = 'SELECT user_id FROM auth WHERE access_token=:access_token;'
        cursor = g.db.execute(query, {'access_token': request.json['access_token']})
        user_id = cursor.fetchone()
        
        if not user_id:
            abort(401)
        
        kwargs['user_id'] = user_id[0]
        
        return f(*args, **kwargs)
        
    return decorated_function


def json_only(f):
    """Decorator that only allows JSON MIME type."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.content_type != JSON_MIME_TYPE:
            error = json.dumps({'error': 'Invalid Content Type'})
            return json_response(error, 400) # 400: Bad Request
        return f(*args, **kwargs)
    return decorated_function
    

def sqlite_date_to_python(date_str):
    """Convert a SQL date to Python datetime."""
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")


def python_date_to_json_str(dt):
    """Converts a Python datetime to JSON format."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S")
    

def json_response(data='', status=200, headers=None):
    """Returns a response with JSON content."""
    headers = headers or {}
    if 'Content-Type' not in headers:
        headers['Content-Type'] = JSON_MIME_TYPE

    return make_response(data, status, headers)
    
def generate_random_token(size=15):
    """Generates a random token."""
    token = ''
    possible_chars = string.ascii_uppercase + string.digits
    for num in range(0, 15):
        token += random.choice(possible_chars)
    return token
