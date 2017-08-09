import sqlite3

from flask import Flask
from flask import g, json, request, jsonify, abort
from .utils import md5, json_only, auth_only, convert_time
import uuid

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
    username = data['username']
    try:
        password = md5(data['password']).hexdigest()
    except KeyError:
        abort(400)
    query = "SELECT id, username, password FROM user WHERE username=?;"
    c = g.db.execute(query, (username,))
    user = c.fetchone()
    if user:
        if password != user[2]:
            abort(401)
        token = str(uuid.uuid4().hex)
        query = """
                INSERT INTO auth ("user_id", "access_token") 
                VALUES (?, ?);
                """
        g.db.execute(query, (user[0], token))
        g.db.commit()
        return jsonify(access_token=token), 201
    abort(404)
    
    
@app.route('/logout', methods=['POST'])
@auth_only
def logout(user_id):
    data = request.get_json()
    query = "SELECT * FROM auth WHERE access_token=:access_token;"
    try:
        params = {'access_token': data['access_token']}
    except KeyError:
        abort(401)
    cursor = g.db.execute(query, params)
    user = cursor.fetchone()
    if user:
        g.db.execute("DELETE FROM auth WHERE access_token=:access_token;", 
                     (data['access_token'],))
        g.db.commit()
        return "", 204
    abort(401)
    
    
@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    query = """
            SELECT id, first_name, last_name, birth_date 
            FROM user 
            WHERE username=?;
            """
    c = g.db.execute(query, (username,))
    profile = c.fetchone()
    if profile:
        user_info = {
            'username': username,
             'user_id': profile[0], 
             'first_name': profile[1], 
             'last_name': profile[2], 
             'birth_date': profile[3],
        }
        query = """
                SELECT id, content, created 
                FROM tweet 
                WHERE user_id=?;
                """
        c = g.db.execute(query, (profile[0],))
        user_info['tweets'] = []
        user_info['tweet_count'] = 0
        for row in c.fetchall():
            tweet_id, created, content = row
            user_info['tweets'].append({
                "id": row[0],
                "text": row[1],
                "date": convert_time(row[2]),
                "uri": "/tweet/{}".format(row[0])
            })
            user_info['tweet_count'] += 1
        return jsonify(user_info), 200
    abort(404)


@app.route('/profile', methods=["POST"])
@json_only
@auth_only
def post_profile(user_id):
    for key in ['first_name', 'last_name', 'birth_date']:
        if key not in request.json:
            abort(400)
    query = """
            UPDATE user
            SET first_name=:first_name, last_name=:last_name,
            birth_date=:birth_date;
            """
    params = {
        'first_name': request.json['first_name'],
        'last_name': request.json['last_name'],
        'birth_date': request.json['birth_date']
    }
    g.db.execute(query, params)
    g.db.commit()
    return "", 201
    
    
@app.route('/tweet/<tweet_id>', methods=['GET'])
def get_tweet(tweet_id):
    query = """
            SELECT t.id, t.content, t.created, u.username 
            FROM tweet t INNER JOIN user u ON (t.id==u.id) 
            WHERE t.id=?
            """
    c = g.db.execute(query, (tweet_id,))
    tweets = c.fetchone()
    if tweets:
        info = {
            'id': tweets[0],
            'content': tweets[1],
            'date': convert_time(tweets[2]),
            'profile': "/profile/{}".format(tweets[3]),
            'uri': "/tweet/{}".format(tweets[0])
        }
        return jsonify(info), 200
    abort(404)
    
    
@app.route('/tweet/<tweet_id>', methods=['DELETE'])
@json_only
@auth_only
def delete_tweet(tweet_id, user_id):
    query = "SELECT t.id, t.user_id FROM tweet t WHERE t.id=:tweet_id;"
    params = {'user_id': user_id, 'tweet_id':tweet_id}
    c = g.db.execute(query, params)
    tweet = c.fetchone()
    if tweet is None:
        abort(404)
    if tweet[1] != user_id:
        abort(401)
    g.db.execute("DELETE FROM tweet WHERE id=?;", (tweet_id,))
    g.db.commit()
    return "", 204


@app.route('/tweet', methods=['POST'])
@json_only
@auth_only
def post_tweet(user_id):
    data = request.get_json()
    query = """
            INSERT INTO tweet ("user_id", "content")
            VALUES (?, ?);
            """
    g.db.execute(query, (user_id, data['content']))
    g.db.commit()
    return "", 201


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
