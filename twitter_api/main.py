import sqlite3

from flask import Flask
from flask import g, json, request, jsonify, redirect
from .utils import _md5
from random import getrandbits

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here
@app.route('/login', methods=['POST'])
def login():
    next = request.args.get('next', '/')
    data = request.get_json()
    username = data['username']
    try:
        password = _md5(data['password'])
    except KeyError:
        return redirect(next, 400)
    query = "SELECT id, username, password FROM user WHERE username=:username;"
    cursor = g.db.execute(query,{'username':username})
    user = cursor.fetchone()
    if user:
        if password != user[2]:
            return redirect(next, 401)
        token = str(getrandbits(32))
        query = 'INSERT INTO auth ("user_id", "access_token") VALUES (:user_id, :access_token);'
        params = {'user_id': user[0], 'access_token':token}
        g.db.execute(query, params)
        g.db.commit()
        return jsonify(access_token=token), 201
    
    return redirect(next, 404)
    
    
@app.route('/logout', methods=['POST'])
def logout():
    next = request.args.get('next', '/')
    data = request.get_json()
    query = "SELECT * FROM auth WHERE access_token=:access_token;"
    try:
        params = {'access_token': data['access_token']}
    except KeyError:
        return redirect(next,401)
    cursor = g.db.execute(query, params)
    user = cursor.fetchone()
    if user:
        g.db.execute("DELETE FROM auth WHERE access_token=:access_token;", (data['access_token'],))
        g.db.commit()
        return redirect(next, 204)
    return redirect(next,401)
    
    
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
                
        
    if request.method == 'GET':

@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
