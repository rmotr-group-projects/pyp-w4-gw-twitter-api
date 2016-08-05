import sqlite3
from flask import Flask, request, Response, abort, g
import random
from hashlib import md5
import json
from .utils import auth_only, json_only
from datetime import datetime
from dateutil.parser import parse

app = Flask(__name__)

def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# Login POST view ##############################################################
@app.route('/login', methods=['POST'])
@json_only
def login():
    
    # Checks to see if 'username' & 'password' keys are in the request.json dictionary.
    # Otherwise 404 error.
    data = request.json
    expected_request_params = ('username', 'password')
    ## Check to see if all the elements in the list comprehension is True
    if not all([param in data for param in expected_request_params]):
      abort(400)
    
    
    users = g.db.execute("SELECT username, password, id FROM user").fetchall()
    for user in users:
        # Checks to see if username exists. 
        # Otherwise 404 error if nothing is returned before the loop finishes.
        if data['username'] == user[0]: 
            # Checks to see if password is correct. Otherwise 401 error.
            if hash_function(data['password']) == user[1]:
                # Checks if user trying to login already has a token active
                # Security first; processing power spent is not worth the security risk of having this before user:pass check
                token = token_exists(data['username'])
                if not token:
                    # If login is succesful return a status code of 201 along with an access token.
                    # INSERT access token into auth table
                    token = generate_token()
                    g.db.execute("INSERT INTO auth (access_token, user_id) VALUES (?, ?)", (token, user[2]))
                    g.db.commit()
                    response_json = json.dumps({'access_token': token})
                    return Response(response_json, status=201, mimetype='application/json')
                else:
                    # Return the token
                    response_json = json.dumps({'access_token': token})
                    return Response(response_json, status=200, mimetype='application/json')
            else:
                abort(401)
    abort(404)

# Logout POST view #############################################################
@app.route('/logout', methods=['POST'])
def logout():
    data = request.json
    # Checks to see if an access token was provided. Otherwise 401 error.
    if 'access_token' not in data:
        abort(401)
        
    # If logout succesful, return status code 204
    g.db.execute("DELETE FROM auth WHERE access_token = ?;", (data['access_token'],))
    g.db.commit()
    
    return Response(status=204)
    

# Profile GET view #############################################################
@app.route('/profile/<username>')
def get_profile(username):
    # Get all data for username
    cursor = g.db.execute("SELECT id, username, first_name, last_name, birth_date \
                        FROM user WHERE username = ?;", (username,))
    query_user = cursor.fetchone()
    
    # Checks to see if the username exists. Otherwise 404 error.
    if query_user:
        cursor = g.db.execute("SELECT id, created, content \
                            FROM tweet WHERE user_id = ?;",(query_user[0],))
        query_tweets = cursor.fetchall()
        
        user_data = { 
                    'user_id': query_user[0],
                    'username': query_user[1],
                    'first_name': query_user[2],
                    'last_name': query_user[3],
                    'birth_date': query_user[4]
                    }
        user_tweets = []
        for tweet in query_tweets:
            new_tweet = {
                        'id': tweet[0],
                        'text': tweet[2],
                        'date': parse(tweet[1]).isoformat(),
                        'uri': "/tweet/{}".format(tweet[0])
                        }
            user_tweets.append(new_tweet)
        user_data['tweet'] = user_tweets
        user_data['tweet_count'] = len(user_tweets)
        
        response_json = json.dumps(user_data)
        return Response(response_json, status=200, mimetype='application/json')
    else:
        abort(404)
 
 
# Profile POST view ############################################################
@app.route('/profile', methods=['POST'])
@auth_only
def post_profile():
    data = request.json
    # Checks to see if all params are provided for update. Otherwise 400 error.
    expected_update_params = ('first_name', 'last_name', 'birth_date')
    if not all([param in data for param in expected_update_params]):
        abort(400)
    
    # Update profile information for user currently logged in.    
    user_id = active_user_id_from_token(data['access_token'])
    query_tuple = (data['first_name'], data['last_name'], data['birth_date'], user_id)
    g.db.execute('UPDATE user SET first_name=?,last_name=?, birth_date=? WHERE id=?;',query_tuple)
    g.db.commit()
    return Response(status=201)


# Tweet GET view ###################################################################
@app.route('/tweet/<tweet_id>', methods=['GET'])
def get_tweet(tweet_id):
    tweet_id = (int(tweet_id),)
    # SELECT some columns from tables tweet and user
    # WHERE the tweet id is the same as the route link tweet id
    # JOIN the rows together based on user IDs from both tables
    joining = g.db.execute("SELECT tweet.id, tweet.content, tweet.created, user.username FROM tweet JOIN user ON \
                tweet.user_id = user.id WHERE tweet.id=?;", tweet_id).fetchone()
    list_of_tweet_ids = g.db.execute("SELECT id FROM tweet;").fetchall()
    
    # Checks to see if the route link tweet id was in the database. Otherwise 404 error.
    if tweet_id not in list_of_tweet_ids:
        abort(404)

    response_dict = {
                      "id": joining[0],
                      "content": joining[1],
                      "date": parse(joining[2]).isoformat(),
                      "profile": "/profile/{}".format(joining[3]),
                      "uri": "/tweet/{}".format(joining[0])
                    }
                    
    response_json = json.dumps(response_dict)
    return Response(response_json, status=200, mimetype='application/json')
    
    
# Tweet POST view ##############################################################
@app.route('/tweet', methods=['POST'])
@auth_only
def post_tweet():
    data = request.json
    # Checks to see if the post contains all fields needed. Otherwise 400 error.
    # auth_only decorator checks for access token already.
    if 'content' not in data:
        abort(400)
    user_id = active_user_id_from_token(data['access_token'])
    query_tuple = (user_id, data['content'])
    # Tweet ID and time posted is automatically added by SQLite3.
    g.db.execute("INSERT INTO tweet (user_id, content) VALUES (?, ?)", query_tuple)
    g.db.commit()
    return Response(status=201)
    
    
# Tweet DELETE view ############################################################
@app.route('/tweet/<tweet_id>', methods=['DELETE'])
@auth_only
def delete_tweet(tweet_id):
    data = request.json
    
    # Fetch user_id from table tweet.
    # Compare it with user_id pertaining to posted access_token.
    user_id = active_user_id_from_token(data['access_token'])
    cursor = g.db.execute("SELECT user_id FROM tweet WHERE id = ?;", (tweet_id,))
    tweet = cursor.fetchone()
    # Checks to see if the tweet exists based on the tweet_id by querying the db. Otherwise 404 error.
    if not tweet:
        abort(404)
    # Checks to see if the tweet corresponds to the user trying to delete it. Otherwise 401 error.
    if tweet[0] != user_id:
        abort(401)
    # Delete the tweet if no abort has been invoked.    
    g.db.execute("DELETE FROM tweet WHERE id = ?;", (tweet_id,))
    g.db.commit()
    return Response(status=204)


def hash_function(text):
    return md5(text.encode('utf-8')).hexdigest()
    
# Simple authentication token generator    
def generate_token():
    hexd = '0123456789abcdefABCDEF'
    random_hexd = random.choice(hexd)
    a_token = md5(random_hexd.encode('utf-8')).hexdigest()
    return a_token
    
# Returns a user id based on token given
def active_user_id_from_token(token):
    user_obj = g.db.execute("SELECT user_id, access_token FROM auth WHERE access_token=?;", (token,)).fetchone()
    return user_obj[0]
    
# Determines whether a token exists via a username, if it does return token, if not return None
def token_exists(username):
    cursor = g.db.execute("SELECT user_id, username, access_token FROM auth JOIN user ON \
            auth.user_id = user.id WHERE username=?;", (username,)).fetchone()
    if cursor:
        return cursor[2]
    else:
        return