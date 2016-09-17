import sqlite3
from datetime import datetime
from flask import Flask
from flask import (g, request, jsonify)
from .utils import *
import json
import time

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
    g.db.commit()
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
@json_only
@auth_only
def profile_update():
    post = request.json
    user_sql = 'SELECT user_id FROM auth WHERE access_token=?'
    user_id = g.db.execute(user_sql, (post['access_token'],)).fetchone()
    if len(post.keys()) != 4:
        return '', 400
    user_sql = '''UPDATE user 
                SET first_name=?,
                    last_name=?,
                    birth_date=?
                    WHERE id=?'''
    g.db.execute(user_sql, (post['first_name'], post['last_name'], post['birth_date'], user_id[0]))
    g.db.commit()
    return "Doing a POST Request", 201
    

@app.route('/tweet/<int:tweet_id>')
def get_tweet(tweet_id):
    tweet_query = '''select t.id, content, created, username from tweet as t join user as u on t.user_id=u.id and t.id=?;'''
    tweet_info = g.db.execute(tweet_query, (tweet_id,)).fetchone()
    if not tweet_info:
        return '', 404
    return_json = {
                   "id" : tweet_info[0],
                   "content" : tweet_info[1],
                   "date" : "T".join(tweet_info[2].split(' ')),
                   "profile" : "/profile/{}".format(tweet_info[3]),
                   "uri" : "/tweet/{}".format(tweet_id)
                  }
    return jsonify(**return_json), 200


@app.route('/tweet', methods=['POST'])
@json_only
@auth_only
def create_tweet():
    post = request.json
    if 'content' not in post:
        return '', 400
    id_query = '''Select user_id from auth where access_token=?'''
    user_id = g.db.execute(id_query, (post['access_token'],)).fetchone()
    tweet_query = '''Insert into tweet (user_id, content) Values (?, ?);'''
    with g.db:
        g.db.execute(tweet_query,(user_id[0], post['content']))
    return '', 201

@app.route('/tweet/<int:tweet_id>', methods=['DELETE'])
@json_only
@auth_only
def del_tweet(tweet_id):
    post = request.json
    auth_query = '''select t.user_id, access_token from tweet as t left outer join auth as a on t.user_id=a.user_id where t.id=?;'''
    auth_info = g.db.execute(auth_query, (tweet_id,)).fetchone()
    if not auth_info:
        return '', 404
    if auth_info[1] != post['access_token']:
        return '', 401
    delete_query = '''DELETE FROM tweet WHERE id=?'''
    with g.db:
        g.db.execute(delete_query,(tweet_id,))
    return '', 204