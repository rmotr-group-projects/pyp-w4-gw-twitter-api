import sqlite3
from datetime import datetime
from flask import Flask
from flask import (g, request, jsonify)
from utils import *

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


@app.route('/login', methods=['POST'])
@json_only
def login():
    
    required_data = ['username', 'password']
    post = request.json
    if not all(data in post for data in required_data):
        return '', 400
    
    user_query = '''Select id, password from user where username = ?;'''
    token_query = '''Select access_token, created from auth where user_id = ?;'''
    add_token ='''Insert into auth (user_id, access_token) Values (?, ?);'''
    update_token = '''Update auth set created=? where user_id=?'''
    
    user_info = g.db.execute(user_query,(post['username'],)).fetchone()
    
    if not user_info:
        return '', 404
    if user_info[1] != md5(post['password']).hexdigest():
        return '', 401
    
    token = g.db.execute(token_query, (user_info[0],)).fetchone()
    if not token:
        token_id = md5("{}{}".format(user_info[0], post['username'])).hexdigest()
        with g.db:
            g.db.execute(add_token, (user_info[0], token_id))
    if token:
        token_id = token[0]
        with g.db:
            g.db.execute(update_token, (datetime.now(), user_info[0]))
    
    token_json = {"access_token": token_id}    
    return jsonify(**token_json), 201


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401


@app.route('/logout', methods=['POST'])
@json_only
@auth_only
def logout():
    post = request.json
    user_logout = """DELETE FROM auth WHERE access_token=?"""
    with g.db:
        g.db.execute(user_logout, (post['access_token'],))
    
    return  '', 204


@app.route('/profile/<username>', methods=['POST'])
@json_only
@auth_only
def profile_view():
    print(request)
    pass
    