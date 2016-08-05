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
        if request.content_type != JSON_MIME_TYPE:
            abort(400)
        elif 'access_token' in request.json:
            # Checks if token exists
            token = str(request.json['access_token'])
            if g.db.execute('SELECT access_token FROM auth WHERE access_token=?',(token,)).fetchone():
                return f(*args, **kwargs)
        abort(401)
    return decorated_function

# Makes sure content is JSON
def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.content_type != JSON_MIME_TYPE:
            abort(400)
        return f(*args, **kwargs)
    return decorated_function
