import sqlite3
from datetime import datetime
from flask import Flask
from flask import (g, request, jsonify)
from utils import *
import json

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])

@app.teardown_appcontext
def close_connection(exception):
    g.db.close()

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
        with g.db: #not needed by adding @app.teardown_appcontext
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
    g.db.execute(user_logout, (post['access_token'],))
    
    return  '', 204

@app.route('/profile/<username>')
def profile_view(username):
    
    def _user_json(username):
        user_keys = ['id', 'username', 'first_name', 'last_name', 'birth_date']
        user_sql = 'SELECT '+(',').join(user_keys)+' FROM user WHERE username=?'
        user_keys = ['user_id'] + user_keys[1:]
        user_info = g.db.execute(user_sql, (username,)).fetchone()
        if not user_info:
            user_info = [None]*len(user_keys)
        return(dict(zip(user_keys,user_info)))
    
    def _tweet_dict(user_id):
        twt_keys = ['id', 'date', 'text', 'uri']
        twt_sql = 'SELECT id, created, content FROM tweet WHERE user_id=?'
        twt_info = g.db.execute(twt_sql, (user_id,)).fetchall()
        
        twt_info = [list(t)+['/tweet/'+str(t[0])] for t in twt_info]
        twt_list = [dict(zip(twt_keys,t)) for t in twt_info]
        return twt_list

    user_info = _user_json(username)
    if not user_info['user_id']:
        return '', 404
    
    tweet_list = _tweet_dict(user_info['user_id'])
    user_info['tweets'] = tweet_list
    user_info['tweet_count'] = len(tweet_list)
    return jsonify(**user_info), 200


@app.route('/profile', methods=['POST'])
def profile_update():
    return "Doing a POST Request", 200
    

