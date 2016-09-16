import sqlite3

from flask import Flask
from flask import g
import json
from .utils import JSON_MIME_TYPE

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])

@app.route('/login', methods=['POST'])
def login():
    pass

@app.route('/logout', methods=['POST'])
def logout():
    pass

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
    
    p_id, username, first_name, last_name, birth_date = profile_data
    profile_json_data = {
        "id": p_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "birth_date": birth_date # Need to convert this date to proper format
    }
    
    tweet_query = """SELECT id, content, created
        FROM tweet
        WHERE user_id = {};
    """
    cur = g.db.execute(tweet_query.format(p_id))
    tweet_data = cur.fetchall()
    
    tweets = []
    for tweet_row in tweet_data:
        t_id, content, created = tweet_row
        tweet = {
            "id": t_id,
            "content": content,
            "date": created, # Need to convert this date/time to proper format
            "uri": "/tweet/%s" % t_id
        }
        tweets.append(tweet)
        
    profile_json_data['tweet'] = tweets
    profile_json_data['tweet_count'] = len(tweets)
    
    return json.dumps(profile_json_data), 200, {'Content-Type': JSON_MIME_TYPE}

    
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
        not_found(404)

    t_id, content, created, username = tweet
    data = {
        "id": t_id,
        "content": content,
        "date": created, # Need to convert this date/time to proper format
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
