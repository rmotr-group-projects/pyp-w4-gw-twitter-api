import sqlite3
import hashlib
import random
import string
from functools import wraps
from flask import Flask, g, abort, Response, request


JSON_MIME_TYPE = 'application/json'


app = Flask(__name__)

def _gen_token(i=6):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(i))

def connect_db(db_name):
    return sqlite3.connect(db_name)

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])

def md5(f):
    return hashlib.md5(f.encode('utf-8'))

def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.content_type != JSON_MIME_TYPE:
            abort(400)
        return f(*args, **kwargs)
    return decorated_function

def auth_only(f):
    @wraps(f)
    @json_only
    def decorated_function(*args, **kwargs):
        info = request.json
        if not 'access_token' in info:
            abort(401)
        token = str(info['access_token'])
        if g.db.execute('SELECT access_token FROM auth WHERE access_token=?',
        (token,)).fetchone():
            return f(*args, **kwargs)
        abort(401)
    return decorated_function

def check_login(f):
    @wraps(f)
    @json_only
    def decorated_function(*args, **kwargs):
        info = request.json
        if not set(['username', 'password']).issubset(set(info.keys())):
            abort(400)
        
        username, password = info['username'], md5(info['password']).hexdigest()
        
        valid_usr = g.db.execute('SELECT id FROM user WHERE username = ?',
                                (username,)).fetchone()
        if not valid_usr:
            abort(404)
        
        valid_pw = g.db.execute('SELECT id from user WHERE username = ? AND \
                                password = ?', (username, password)).fetchone()
        
        if not valid_pw:
            abort(401)
        
        kwargs['access_token'] = _gen_token()
        kwargs['usr_id'] = valid_usr[0] 
        
        return f(*args, **kwargs)
    return decorated_function