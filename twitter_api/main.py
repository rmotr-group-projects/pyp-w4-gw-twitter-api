import sqlite3

from flask import Flask, g, request, url_for, Response, abort
import json
from .utils import *
from hashlib import md5

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here

@json_only
@app.route('/login', methods = ['POST'])
def login():    # jon working on
    # Inputs: username and password
    # Ouputs: generated new access token for given username.
    authdata = request.get_json()
    
    try:
        username = authdata['username']
        password = authdata['password']
        password = md5(password).hexdigest()
    except KeyError:
        abort(400)

    db_authdata = g.db.execute('SELECT password, id from user WHERE username = ?', (username,))
    pass_and_id = db_authdata.fetchone()
    if pass_and_id:
        passdata, uid = pass_and_id
    else:
        passdata = None
        
    if not passdata: # no entry in DB.  should be 400, but tests asks for 404.
        abort(404)
    
    if passdata != password:
        abort(401)
    
    usertoken = generate_token()
    
    g.db.execute('INSERT INTO auth (user_id, access_token) VALUES (?, ?)', (uid, usertoken))
    g.db.commit()
    
    return Response(json.dumps(dict(access_token = usertoken)), status=201, content_type=JSON_MIME_TYPE)


@auth_only
@json_only
@app.route('/logout', methods = ['POST'])
def logout(): # Prashant is trying this now
    uid = token_to_uid(request)
    g.db.execute('DELETE FROM auth WHERE user_id = ?', (uid,))
    g.db.commit()
    return Response('', status=204)


@auth_only
@json_only
@app.route('/profile', methods = ['POST'])
def write_profile():
    pass


@app.route('/profile', methods = ['GET'])
def read_profile():
    pass

@json_only
@app.route('/tweet', methods = ['POST'])
def new_tweet():
    pass

@app.route('/tweet/<id>', methods = ['GET']) # lana
def read_tweet():
    pass

@json_only
@auth_only
@app.route('/tweet/<id>', methods = ['DELETE'])
def delete_tweet():
    pass


# helper functions
def token_to_username(token): # jon
    # returns a username given a token
    pass

def token_to_uid(request): # jon
    # returns a username given a token
    if 'access_token' not in request.get_json():
        abort(401)
    else:    
        token = request.get_json()['access_token']

    uid_results = g.db.execute('SELECT user_id FROM auth WHERE access_token = ?', (token,))
    uid = uid_results.fetchone()
    if uid:
        return uid[0]
    else:
        abort(404)

def generate_token():  # jon
    return 'foo'
    # TODO: REAL CODE HERE PLEASE!

# pre-written handlers.  wrapped in Response.
@app.errorhandler(404)
def not_found(e):
    return Response('', 404)


@app.errorhandler(401)
def not_found(e):
    return Response('', 401)
