import sqlite3
import string
import random

from flask import Flask, g, make_response, jsonify, request
import json
from .utils import JSON_MIME_TYPE, md5

app = Flask(__name__)

def auth_token_generator(size = 6, chars = string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])

@app.route('/login', methods=['POST'])
def login():
    username = request.get_json()['username'].strip()
    
    query = """SELECT id, username, password
        FROM user WHERE username = {};
    """
    cur = g.db.execute(query.format(username))
    logged_in_profile = cur.fetchall
    
    password = request.get_json()['password']
    
    if len(password) == 0:
        unauthorized('')
    
    md5_password = md5(password)
    
    if md5_password != logged_in_profile[0][2]:
        unauthorized('')
    else:
        auth_token = auth_token_generator()
        
        query = '''INSERT INTO 'auth' ('user_id', 'access_token')
                VALUES ('{0}', '{1}');
        '''
        g.db.execute(query.format(logged_in_profile[0][2]))
        g.db.commit()
        
        auth_data = {
            'access_token': auth_token
        }
        
        return make_response(jsonify(auth_data), 201)
    
    
@app.route('/logout', methods=['POST'])
def logout():
    query = '''DELETE FROM auth
            WHERE access_token = '{}'
    '''
    g.db.execute(query.format(request.json['access_token']))
    g.db.commit()
    
    
app.route('/profile')
def update_profile():
    pass

app.route('/profile/<username>', methods = ['GET'])
def get_profile(username):
    profile_query = """SELECT id, username, first_name, last_name, birth_date
        FROM user WHERE username = {};
    """
    cur = g.db.execute(profile_query.format(username))
    profile_data = cur.fetchall()
    
    if profile_data is None:
        not_found('')
    
    p_id, user_name, first_name, last_name, birth_date = profile_data
    profile_json_data = {
        "id": p_id,
        "username": user_name,
        "first_name": first_name,
        "last_name": last_name,
        "birth_date": str(birth_date), # Need to convert this date to proper format
    }
    
    tweet_query = """SELECT id, content, created
        FROM tweet
        WHERE user_id = {};
    """
    cur = g.db.execute(tweet_query.format(profile_json_data['id']))
    tweet_data = cur.fetchall()
    
    tweets = []
    for tweet_row in tweet_data:
        t_id, content, created = tweet_row
        tweet = {
            "id": t_id,
            "content": content,
            "date": str(created), # Need to convert this date/time to proper format
            "uri": "/tweet/%s" % t_id
        }
        tweets.append(tweet)
        
    profile_json_data['tweet'] = tweets
    profile_json_data['tweet_count'] = len(tweets)
    
    return make_response(jsonify(profile_json_data), 200)

    
@app.route('/tweet/<tweet_id>')
def create_tweet():
    pass

@app.route('/tweet/<tweet_id>')
def delete_tweet():
    pass

@app.route('/tweet/<int:tweet_id>', methods = ['GET'])
def get_tweet(tweet_id):
    query = """SELECT t.id, t.content, t.created, u.username
        FROM tweet t INNER JOIN user u ON u.id == t.id
        WHERE t.id=:tweet_id;
    """

    cursor = g.db.execute(query, {'tweet_id': tweet_id})
    tweet = cursor.fetchone()
    if tweet is None:
        not_found('')

    t_id, content, created, username = tweet
    data = {
        "id": t_id,
        "content": content,
        "date": str(created), # Need to convert this date/time to proper format
        "profile": "/profile/%s" % username,
        "uri": "/tweet/%s" % t_id
    }
    return json.dumps(data), 200, {'Content-Type': JSON_MIME_TYPE}



@app.errorhandler(404)
def not_found(e):
    return '', 404

@app.errorhandler(401)
def unauthorized(e):
    return '', 401
    
@app.errorhandler(400)
def bad_request(e):
    return '', 400

