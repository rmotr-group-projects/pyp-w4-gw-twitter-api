import sqlite3

from os import urandom
from base64 import b64encode
from flask import Flask
from flask import g, request, jsonify
from twitter_api.utils import md5, json_only, auth_only

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here
@app.route('/login', methods=['POST', 'GET'])
@json_only
def login():
    if request.method == 'POST':
        data = request.get_json()
        
        if 'password' not in data:
            return 'Missing password', 400
        
        params = {
            'username': data['username'],
            'password': md5(data['password']).hexdigest()
        }
        cursor = g.db.execute('SELECT * FROM user WHERE username = :username AND password = :password;', params)
        user = cursor.fetchone()
        if user:
            # generate token
            random_bytes = urandom(64)
            access_token = b64encode(random_bytes).decode('utf-8')
            # insert into auth
            params = {'user_id' : user[0], 'access_token' : access_token}
            g.db.execute('INSERT INTO auth (user_id, access_token) VALUES (:user_id, :access_token);', params)
            g.db.commit()
            return (jsonify({'access_token': access_token}), 201)
        
        cursor = g.db.execute('SELECT * FROM user WHERE username = :username OR password = :password;', params)
        user = cursor.fetchone()
        if user[1] == params['username']:
            return 'Incorrect Password', 401
        else:
            return 'Username does not exists', 404


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
