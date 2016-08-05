from functools import wraps
from hashlib import md5
from flask import request, abort, Flask, g
import sqlite3

JSON_MIME_TYPE = 'application/json'

app = Flask(__name__)

def connect_db(db_name):
    return sqlite3.connect(db_name)

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])

# Checks request token
def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' in kwargs:
            # Checks if token exists
            if g.db.execute('SELECT access_token FROM auth WHERE access_token=?',(kwargs['access_token'])).fetchone():
                return f(*args, **kwargs)
        abort(401)
    return decorated_function

# Make sure content is suppose to be JSON
def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.content_type != JSON_MIME_TYPE:
            abort(400)
        return f(*args, **kwargs)
    return decorated_function
