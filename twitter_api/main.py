import sqlite3

from flask import Flask, g, jsonify, abort, request
import utils
from datetime import datetime

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])
    g.db.row_factory = sqlite3.Row


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
    
def tweetdict(tweet):
    return {
    'id': tweet['id'],
    'content': tweet['content'],
    'date': "T".join(tweet['created'].split()),
    'uri': '/tweet/{}'.format(tweet['id'])}
    
@app.route('/tweet', methods = ['POST'])
def post_tweet():
    if not request.is_json:
        abort(400)
    received = request.get_json()
    if 'access_token' not in received:
        abort(401)
    token = received['access_token']
    content = received['content']
    cursor = g.db.cursor()
    cursor.execute('SELECT user_id FROM auth WHERE access_token = ?', (token,))
    user = cursor.fetchone()
    if not user:
        abort(401)
    user_id = user['user_id']
    cursor.execute('INSERT INTO tweet (user_id, content) VALUES (?, ?)', (user_id, content))
    g.db.commit()
    return '', 201

@app.route('/tweet/<int:tweetid>', methods = ['GET', 'DELETE'])
def get_or_delete_tweet(tweetid):
    if request.method == 'GET':
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT *
            FROM tweet t INNER JOIN user u 
            ON t.user_id = u.id 
            WHERE t.id = ?
        """, (tweetid,))
        tweetdata = cursor.fetchone()
        if not tweetdata:
            abort(404)
        return jsonify(profile = '/profile/{}'.format(tweetdata['username']) , **tweetdict(tweetdata))
    elif request.method == 'DELETE':
        token = request.get_json()['access_token']
        cursor = g.db.cursor()
        cursor.execute('SELECT user_id FROM auth WHERE access_token = ?', (token,))
        user = cursor.fetchone()
        if not user:
            abort(401)
        user_id = user['user_id']
        cursor.execute('SELECT user_id FROM tweet WHERE id = ?', (tweetid,))
        tweetdata = cursor.fetchone()
        if not tweetdata:
            abort(404)
        if tweetdata['user_id'] == user_id:
            cursor.execute('DELETE FROM tweet where id = ?', (tweetid,))
            g.db.commit()
            return '', 204
        else:
            abort(401)
    
@app.route('/profile', methods = ['POST'])
def set_profile():
    if not request.is_json:
        abort(400)
    received = request.get_json()
    if not all(key in received for key in ['first_name', 'last_name', 'birth_date']):
        abort(400)
    if 'access_token' not in received:
        abort(401)
    cursor = g.db.cursor()
    cursor.execute('SELECT user_id FROM auth WHERE access_token = ?', (received['access_token'],))
    user = cursor.fetchone()
    if not user:
        abort(401)
    cursor.execute('UPDATE user SET first_name = ?, last_name = ?, birth_date = ? WHERE id = ?',
        (received['first_name'], received['last_name'], received['birth_date'], user['user_id']))
    g.db.commit()
    return '', 201

@app.route('/profile/<string:username>')
def get_profile(username):
    cursor = g.db.cursor()
    cursor.execute("""
        SELECT u.id, u.username, u.first_name, u.last_name, u.birth_date
        FROM user u
        WHERE u.username = ?
    """, (username,))
    userdata = cursor.fetchone()
    if not userdata:
        abort(404)
    cursor.execute("""
        SELECT *
        FROM tweet t INNER JOIN user u 
        ON t.user_id = u.id
        WHERE u.username = ?
        """, (username,))
    usertweets = [tweetdict(row) for row in cursor]
    for tweet in usertweets:
        tweet['text'] = tweet['content']
        del tweet['content']
    
    return jsonify(user_id = userdata['id'], username = userdata['username'], 
        first_name = userdata['first_name'], last_name = userdata['last_name'],
        birth_date = userdata['birth_date'], tweets = usertweets, 
        tweet_count = len(usertweets))
        
@app.route('/login', methods = ['POST'])
def login():
    received = request.get_json()
    username = received['username']
    if 'password' not in received:
        abort(400)
    password = utils.md5(received['password']).hexdigest()
    cursor = g.db.cursor()
    cursor.execute('SELECT id, password FROM user WHERE username = ?', (username,))
    id_and_pass = cursor.fetchone()
    if not id_and_pass:
        abort(404)
    if id_and_pass['password'] != password:
        abort(401)
    token = utils.md5(username + received['password'] + str(datetime.now())).hexdigest()
    cursor.execute('INSERT INTO auth (user_id, access_token) VALUES (?, ?)', (id_and_pass['id'], token))
    g.db.commit()
    return jsonify(access_token = token), 201
    
    
@app.route('/logout', methods = ['POST'])
def logout():
    received = request.get_json()
    if not 'access_token' in received:
        abort(401)
    token = received['access_token']
    cursor = g.db.cursor()
    cursor.execute('SELECT user_id FROM auth WHERE access_token = ?', (token,))
    user_id = cursor.fetchone()['user_id']
    cursor.execute('DELETE FROM auth WHERE user_id = ?', (user_id,))
    g.db.commit()
    return '', 204