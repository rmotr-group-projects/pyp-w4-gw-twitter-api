import sqlite3
import time
from . utils import md5, query_db, json_only, auth_only, get_user_id

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

    user_id = get_user_id(request)
    
    query_db('INSERT INTO tweet(user_id, content) VALUES (?, ?)', [user_id, content])
    g.db.commit()
    
    return '', 201


@app.route('/tweet/<int:t_id>', methods=['GET'])
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
def delete_tweet(t_id):
    data = request.get_json()
    user_id = get_user_id(request)
    query = query_db('SELECT user_id FROM tweet WHERE id = ?', [t_id], one=True)
    if query is None:
        abort(404)
    if user_id != query['user_id']:
        abort(401)

    query_db('DELETE FROM tweet WHERE id = ?', [t_id])
    g.db.commit()
    return '', 204
    
@app.route('/profile/<username>')
def profile(username):
    data = request.get_json()
    userdata = query_db('''SELECT id, first_name, last_name, birth_date
                        FROM user WHERE username = ?''', [username], one=True)
    if userdata is None:
        abort(404)
    
    
    
    tweetdata = query_db('SELECT * FROM tweet WHERE user_id = ?', [userdata['id']])
    
    tweets = []
    for t in tweetdata:
        tweets.append({
            'date': t['created'].replace(' ', 'T'),
            'id': t['id'],
            'text': t['content'],
            'uri': '/tweet/{}'.format(t['id'])
        })
    
    return jsonify(user_id = userdata['id'],
                   username = username,
                   first_name = userdata['first_name'],
                   last_name = userdata['last_name'],
                   birth_date = userdata['birth_date'],
                   tweets = tweets,
                   tweet_count = len(tweets)), 200
    

@app.route('/profile', methods=['POST'])
@auth_only
@json_only
def update_profile():
    user_id = get_user_id(request)
    
    data = request.get_json()
    req_fields = set(['first_name', 'last_name', 'birth_date'])
    if not req_fields.issubset(set(data.keys())):
        abort(400)
    
    query_db("""UPDATE user
                SET first_name=?, last_name=?, birth_date=?
                WHERE id=?""", [data['first_name'], data['last_name'], data['birth_date'], user_id])
    g.db.commit()
    return '', 201


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
