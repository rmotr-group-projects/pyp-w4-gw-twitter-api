import sqlite3

from flask import Flask
from flask import g
from flask import request, Response, abort
import random
from hashlib import md5
import json
from .utils import auth_only, json_only


app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# Login POST view ###################################################################
@app.route('/login', methods=['POST'])
@json_only
def login():

    data = request.json
    expected_request_params = ('username', 'password')
    if not all([param in data for param in expected_request_params]):
       abort(400)
    
    # Checks if user trying to login already has a token active
    if not g.db.execute("SELECT user_id, username FROM auth JOIN user ON auth.user_id = user.id WHERE username=?;", (data['username'],)).fetchall():
        pass
    
    users = g.db.execute("SELECT username, password, id FROM user").fetchall()
    for user in users:
        # Checks to see if username exists. Otherwise 404 error.
        if data['username'] == user[0]: 
            # Checks to see if password is correct. Otherwise 401 error.
            if hash_function(data['password']) == user[1]:
                # If login is succesful -> 201
                # INSERT access token into access table
                token = generate_token()
                g.db.execute("INSERT INTO auth (access_token, user_id) VALUES (?, ?)", (token, user[2]))
                g.db.commit()
                response_json = json.dumps({'access_token': token})
                return Response(response_json, status=201, mimetype='application/json')
            else:
                abort(401)
    abort(404)

# Logout POST view ###################################################################
@app.route('/logout', methods=['POST'])
def logout():
    data = request.json
    if 'access_token' not in data:
        abort(401)
        
    # If logout succesful, return 204
    g.db.execute("DELETE FROM auth WHERE access_token = ?;", (data['access_token'],))
    g.db.commit()
    
    return Response(status=204)
    

# Profile GET view #################################################################
@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    # Get all data for username
    connect_db.text_factory = str

    cursor = g.db.execute("SELECT id, username, first_name, last_name, birth_date \
        FROM user WHERE username = ?;", (username,))
    query_user = cursor.fetchone()
    if query_user:
    
        cursor = g.db.execute("SELECT id, created, content \
                                        FROM tweet WHERE user_id = ?;",(query_user[0],))
        query_tweets = cursor.fetchall()
        
        user_data = { 
            'user_id': query_user[0].encode('utf-8'), 
            'username': query_user[1].encode('utf-8'),
            'first_name': query_user[2].encode('utf-8'),
            'last_name': query_user[3].encode('utf-8'),
            'birth_date': query_user[4]
        }
        user_tweets = []
        for tweet in query_tweets:
            new_tweet = {
                'id': tweet[0],
                'text': tweet[2].encode('utf-8'),
                'date': tweet[1],
                'uri': "/tweet/{}".format(tweet[0])
            }
            user_tweets.append(new_tweet)
        
        user_data['tweets'] = user_tweets
        user_data['tweet_count'] = len(user_tweets)

        response_json = json.dumps(user_data, encoding='utf8')
        return Response(response_json, status=200, mimetype='application/json')
    else:
        return Response(status=404)
 
 
# Profile POST view #################################################################
@app.route('/profile', methods=['POST'])  
def post_profile():
    
    
    
    
    return Response(status=404)
    

# Tweet POST view ###################################################################
@app.route('/tweet', methods=['POST'])
def tweet():
    return Response(status=200)

@app.errorhandler(404)
def not_found(e):
    return 'Page not found', 404

@app.errorhandler(401)
def not_found(e):
    return 'Not Authorized?', 401

def generate_token():
    return '1234'
    
def hash_function(text):
    return md5(text.encode('utf-8')).hexdigest()
    

    