import sqlite3
import time
from . utils import md5, query_db, json_only, auth_only

from flask import Flask
from flask import g, request, jsonify, abort

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here


@app.route('/login', methods=['POST'])
@json_only
def login():
    data = request.get_json()
    
    if 'username' not in data.keys():
        abort(400)
    username = data['username']
    
    if 'password' not in data.keys():
        abort(400)
    password = md5(data['password']).hexdigest()
    
    query = query_db('SELECT id, password FROM user WHERE username = ?', [username], one=True)
    
    if query is None:
        abort(404)
        
    if query['password'] != password:
        abort(401)
    
    user_id = query['id']
    
    token = md5(username + str(time.time())).hexdigest()
    
    query_db('INSERT INTO auth (user_id, access_token) VALUES (?, ?)', [user_id, token])
    g.db.commit()
    
    return jsonify(access_token=token), 201


@app.route('/logout', methods=['POST'])
@auth_only
def logout():
    data = request.get_json()
    token = data.get('access_token', None)
    if not token:
        abort(401)
    
    query_db('DELETE FROM auth WHERE access_token = ?', [token])
    g.db.commit()
    
    return '', 204
    
@app.route('/tweet', methods=['POST'])
@json_only
@auth_only
def post_tweet():
    data = request.get_json()
    content = data.get('content', None)
    
    if content is None:
        abort(401)

    query = query_db('SELECT user_id FROM auth WHERE access_token = ?', [data['access_token']], one=True)
    
    user_id = query['user_id']
    
    query_db('INSERT INTO tweet(user_id, content) VALUES (?, ?)', [user_id, content])
    g.db.commit()
    
    return '', 201


@app.route('/tweet/<int:t_id>')
def tweet(t_id):
    tweet = query_db('SELECT t.content, t.created, u.username FROM tweet t INNER JOIN user u ON t.user_id = u.id WHERE t.id = ?', [t_id], one=True)

    if not tweet:
        abort(404)

    return jsonify(id = t_id,
                   content = tweet['content'],
                   date = tweet['created'].replace(' ', 'T'),
                   profile = '/profile/{}'.format(tweet['username']),
                   uri = '/tweet/{}'.format(t_id)), 200

@app.route('/tweet/<int:t_id>', methods=['DELETE'])
@json_only
@auth_only



@app.route('/profile/<username>')
def profile(username):
    pass


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
