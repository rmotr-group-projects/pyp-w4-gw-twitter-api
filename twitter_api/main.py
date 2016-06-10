# -*- coding: utf-8 -*-
import json
import sqlite3

from datetime import datetime
import dateutil.parser as du
from flask import abort, Flask, g, request, Response
from hashlib import md5
from random import choice
from string import ascii_lowercase, digits

from .utils import auth_only, JSON_MIME_TYPE, json_only


app = Flask(__name__)


#############################
# Helper functions:         #
#############################
def connect_db(db_name):
    return sqlite3.connect(db_name)

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])

def _hash_password(password):
    '''
    Returns the MD5 hash of the user's entered password
    '''
    # password_bytes = str.encode(password)
    password_bytes = password.encode('utf-8')
    return md5(password_bytes).hexdigest()

def _generate_access_token():
    '''
    Returns a new access token for an authenticated user
    '''
    values = ascii_lowercase + digits
    token = ''
    for _ in range(10):
        token += choice(values)
    return token

@auth_only
def _check_login():
    '''
    Checks if the user is already logged in.
    '''
    # Obtain user_id and db_token
    query = '''SELECT user_id, access_token
               FROM auth
               WHERE access_token=?;'''
    cursor = g.db.execute(query, (str(request.json['access_token']),))
    results = cursor.fetchone()
    return results
    
def _get_existing_user_data(username):
    # Obtain existing data from user DB
    query = '''SELECT id, first_name, last_name, birth_date 
               FROM user
               WHERE username=?;'''
    cursor = g.db.execute(query, (username,))
    results = cursor.fetchone()
    if results:
        return results
    else:
        abort(404)
    
def _get_existing_tweet(tweet_id):
    # Obtain existing data from tweet DB
    query = '''SELECT id, user_id, created, content
               FROM tweet
               WHERE id=?;'''
    cursor = g.db.execute(query, (tweet_id,))
    results = cursor.fetchone()
    if results:
        return results
    else:
        abort(404)
    
@auth_only
def _delete_existing_tweet(tweet_id, user_id):
    # Obtain existing data from tweet DB
    query = '''SELECT id, user_id
               FROM tweet
               WHERE id=? AND user_id=?;'''
    cursor = g.db.execute(query, (int(tweet_id), (int(user_id))))
    results = cursor.fetchone()
    if results:
        query = '''DELETE FROM tweet WHERE id=?;'''
        g.db.execute(query, (int(tweet_id),))
        g.db.commit()
        return True
    return False

def _get_username_from_userid(user_id):
    query = '''SELECT username
               FROM user
               WHERE id=?;'''
    cursor = g.db.execute(query, (user_id,))
    return cursor.fetchone()[0]


#############################
# Views:                    #
#############################
@app.route('/', methods=['GET'])
def base():
    return Response(status=204)

@app.route('/login', methods=['POST'])
def login():
    
    # Verify the correct data was submitted
    if any(val not in request.json for val in {'username', 'password'}):
        abort(400)
    
    # Get submitted data for authentication
    un = request.json['username']
    pw = _hash_password(request.json['password'])
    
    # Verify that a user exists who matches the submitted username
    query = 'SELECT COUNT(*) FROM user WHERE username=?;'
    count = g.db.execute(query, (un,)).fetchone()[0]
    if count == 0:
        abort(404)
    
    # Find the user id of the user whose data match the submitted data
    query = 'SELECT id FROM user WHERE username=? AND password=?;'
    cursor = g.db.execute(query, (un, pw))
    results = cursor.fetchone()
    
    # If there is an entry in the query result, store it as the user id
    if results:
        uid = results[0]
    
    # If the user fails authentication, return 401
    else:
        abort(401)
    
    # Generate an access token
    ACCESS_TOKEN = _generate_access_token()
    
    # Store access token in *auth* table
    query = 'INSERT INTO "auth" ("user_id", "access_token") VALUES (?, ?);'
    g.db.execute(query, (int(uid), ACCESS_TOKEN))
    g.db.commit()
    response = Response(
        json.dumps({'access_token': ACCESS_TOKEN}),
        status=201,
        mimetype=JSON_MIME_TYPE
    )
    
    return response
    

@app.route('/logout', methods=['POST'])
@auth_only
def logout():
    '''
    Logs out the user by removing the user's access token from the auth table
    '''
    
    # Remove the access token
    query = 'DELETE FROM auth WHERE access_token=?;'
    g.db.execute(query, (request.json['access_token'],))
    g.db.commit()
    
    # Return a No Content response
    return Response(status=204)

@app.route('/profile', methods=['POST'])
def update_profile():
    
    # Check if user is logged in. (user_id, access_token)
    (user_id, db_token) = _check_login()
    username = _get_username_from_userid(user_id)
    if db_token:
        # Obtain existing data from user DB
        (user_id, fn, ln, dob) = _get_existing_user_data(username)
        
        # Update new values in DB for those provided.
        query = '''UPDATE user 
                SET first_name=?, last_name=?, birth_date=? 
                WHERE id=?;'''
        fn = request.json['first_name'] or fn
        ln = request.json['last_name'] or ln
        dob = request.json['birth_date'] or dob
        g.db.execute(query, (fn, ln, dob, user_id))
        g.db.commit()
        
        # 201 - Success
        return Response(status=201) 
    else:
        # 401 - Missing acces token, invalid access
        return Response(status=401) 
    # 400 - Missing requirement, not json
    return Response(status=400) 

@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    # Obtain existing data from user DB
    (user_id, first_name, last_name, birth_date) = _get_existing_user_data(username)
    user_data = {
        'user_id': user_id,
        'username': username,
        'first_name': first_name,
        'last_name': last_name,
        'birth_date': birth_date
    }
    
    # Obtain list of all user tweets by tweet-id
    query = '''SELECT id FROM tweet WHERE user_id=?;'''
    cursor = g.db.execute(query, (user_id,))
    results = list(cursor.fetchall())
    user_data['tweet'] = []
    
    for tweet_id in results:
        (tweet_id, user_id, created, content) = _get_existing_tweet(tweet_id[0])
        user_data['tweet'].append({
            "id": tweet_id,
            "text": str(content),
            "date": du.parse(created).isoformat(),
            "uri": "/tweet/{}".format(tweet_id)
        })
    
    user_data['tweet_count'] = len(user_data['tweet'])
    
    # 200 - Success
    response = Response(
        json.dumps(user_data),
        status=200,
        mimetype=JSON_MIME_TYPE
    )
    return response

@app.route('/tweet/<int:tweet_id>', methods=['GET', 'DELETE'])
def tweet(tweet_id):
    
    # Check if user is logged in. (user_id, access_token)
    (tweet_id, user_id, created, content) = _get_existing_tweet(tweet_id)
    # username = _get_username_from_userid(user_id)
    
    # Check for user authentication and DELETE method
    if request.method == 'DELETE':
        
        # Verify that an access token was passed
        if 'access_token' in request.json:
            
            # Verify that the token is valid
            query = 'SELECT user_id FROM auth WHERE access_token=?;'
            cursor = g.db.execute(query, (request.json['access_token'],))
            results = cursor.fetchone()
            
            # If the token is valid, try to delete the tweet
            if results:
                user_id = results[0]
                # Pass tweet_id to function for check and possible deletion
                if _delete_existing_tweet(tweet_id, user_id):
                    
                    # Return a Success response
                    return Response(status=204)
        
        # If user attempting to delete another user's tweet, or user did not
        #  authenticate, return an Unauthorized response
        abort(401)
    
    # Obtain existing data from user DB
    username = _get_username_from_userid(user_id)
    tweet_details = {
        "id": tweet_id,
        "content": str(content),
        "date": du.parse(created).isoformat(),
        "profile": "/profile/{}".format(username),
        "uri": "/tweet/{}".format(tweet_id)
    }
    
    # Create a response
    response = Response(
        json.dumps(tweet_details),
        status=200,
        mimetype=JSON_MIME_TYPE
    )
    
    return response

@app.route('/tweet', methods=['POST'])
@auth_only
def post_tweet():
    # Get user_id that matches the access token passed
    (user_id, db_token) = _check_login()
    
    # Validate tweet content
    if 'content' not in request.json:
        abort(404) # Might not be the best code. Maybe 400?
    elif not (0 < len(request.json['content']) <= 140):
        abort(404) # Might not be the best code.  Maybe 400?
    
    # Add the tweet to the tweet db table
    query = 'INSERT INTO "tweet" ("user_id", "content") VALUES (?, ?);'
    g.db.execute(query, (user_id, request.json['content']))
    g.db.commit()
    
    # Return a Created response
    return Response(status=201)


#############################
# Error handlers:           #
#############################
@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401



