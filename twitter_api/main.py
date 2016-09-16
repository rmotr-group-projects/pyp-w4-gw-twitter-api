import sqlite3
import json
from flask import (Flask, g, request, abort)
import random
from .utils import md5


app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here

@app.route('/login', methods=['POST'])
def login():
    if not request.json or not 'username' in request.json or not 'password' in request.json:
        abort(400)
    username = request.json.get('username', "")
    password = request.json.get('password', "")
    check_user = username_password(username, password)
    if not check_user[0]:
        abort(404)
    if not check_user[1]:
        abort(401)
    token = random.SystemRandom().random()
    access_token={
                "access_token": str(token),
                }
    user_id = convert_username_to_id(username)
    insert_token(user_id, access_token['access_token'])
    return json.dumps(access_token), 201

@app.route('/logout', methods=['POST'])
def logout():
    if not request.json or not 'access_token' in request.json:
        abort(401)
    token = request.json.get('access_token')
    curs = g.db.execute('SELECT * FROM auth')
    data = curs.fetchall()
    for x in data:
        if token in x:
            id = x[0]
    g.db.execute('DELETE FROM auth WHERE id=%s' % id)
    g.db.commit()
    #check
    return '', 204

#helper functions
def username_password(username, password):
    curs = g.db.execute('SELECT * FROM user')
    data = curs.fetchall()
    arr = []
    for x in data:
        if username in x:
            arr.append(1)
            if md5(password).hexdigest() in x:
                arr.append(1)
            else:
                arr.append(0)
    if not arr:
        arr = [0, 0]
    return arr

def insert_token(user_id, token):
    curs = g.db.execute('INSERT INTO auth (user_id, access_token) VALUES (%s, "%s")'%(user_id, token))
    g.db.commit()
    curs = g.db.execute('select * from auth')

def convert_username_to_id(username):
    users_cursor = g.db.execute('SELECT * FROM user')
    users_data = users_cursor.fetchall()
    for x in users_data:
        if username in str(x):
            return x[0]



@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
