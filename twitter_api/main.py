import sqlite3

from flask import Flask
from flask import g
from flask import request, Response, abort
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
            'user_id': query_user[0],
            'username': query_user[1],
            'first_name': query_user[2],
            'last_name': query_user[3],
            'birth_date': query_user[4]
        }
        user_tweets = []
        for tweet in query_tweets:
            dateISO = parse(tweet[1]).isoformat()

            # print(dateISO)
            # Expected Date: 2016-06-01T05:13:00
            # Result = 2016-06-01 05:13:00
            # dateiso = datetime.strptime(tweet[1],'%Y-%m-%d ').isoformat()
            # print(tweet[1])
            # print(type(tweet[1]))

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
 
 
# Profile POST view #################################################################
# auth_only already checks if there is token in place
@app.route('/profile', methods=['POST'])
@auth_only
def post_profile():
    data = request.json
    update_param_check = ('first_name', 'last_name', 'birth_date')
    if all([param in data for param in update_param_check]):
        user_id = active_user_from_token(data['access_token'])
        datetime_birthday = parse(data['birth_date'])
        query_tuple = (data['first_name'], data['last_name'], datetime_birthday, user_id)
        g.db.execute('UPDATE user SET first_name=?,last_name=?, birth_date=? WHERE id=?;',query_tuple)
        g.db.commit()
        return Response(status=201)
    else:
        return abort(400)

# Tweet POST view ###################################################################
# auth_only already checks if there is token in place
@app.route('/tweet', methods=['POST'])
@auth_only
def tweet():
    return Response(status=200, mimetype='application/json')

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
    
def action_query(query, subs):
    g.db.execute(query, subs)
    g.db.commit()
    return

# Returns a user id based on token given
def active_user_from_token(token):
    user_obj = g.db.execute("SELECT user_id, access_token FROM auth WHERE access_token=?;", (token,)).fetchone()
    return user_obj[1]
