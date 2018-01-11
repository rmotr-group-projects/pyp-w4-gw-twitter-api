import sqlite3
from flask import Flask, g, make_response, abort, request, session
from twitter_api.utils import (sqlite_date_to_python, python_date_to_json_str, 
                               json_response, auth_only, json_only, md5, 
                               generate_random_token)
import json

app = Flask(__name__)

JSON_MIME_TYPE = 'application/json'

def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


@app.route('/login', methods=['POST'])
def login():
    """Logs the user into their account."""
    # Get the json data posted by the user
    data = request.json
    
    if not all([data.get('username'), data.get('password')]):
        # Error: Cannot have missing data
        error = json.dumps({'error': 'Missing field/s (username, password)'})
        return json_response(error, 400) # 400: Bad Request
    
    # Check that the user exists in the database
    user_query = 'SELECT * FROM user WHERE username=:username;'
    cursor = g.db.execute(user_query, {'username': data.get('username')})
    user_data = cursor.fetchone() # (id, username, password, first_name, last_name, birthdate)
    if not user_data:
        # The user does not exist
        abort(404)
    
    if md5(data.get('password')).hexdigest() != user_data[2]:
        # Incorrect password
        abort(401)
    
    # Get the user's ID from the tuple
    user_id = user_data[0]
    
    # Do not allow duplicate access tokens
    while True:
        # Create new token
        token = generate_random_token()
        
        # Get all tokens
        cursor = g.db.execute('SELECT access_token FROM auth;')
        token_list = cursor.fetchall()
        
        # Check if the database has any tokens
        if token_list:
            # Clean up the token list
            token_list = [t[0] for t in token_list]
            
            # If the new token is in the database, make a different one
            if token in token_list:
                continue
        # No duplicate token found
        break
    
    # Insert the access token into the database
    insert_query = """INSERT INTO auth ('user_id', 'access_token') VALUES (?, ?);"""
    g.db.execute(insert_query, (user_id, token))
    g.db.commit()
    
    # Store the token data in a dictionary
    data = {'access_token': token}
    
    # Serialize the data as a json formatted stream
    json_content = json.dumps(data)
    
    return make_response(json_content, 201, {'Content-Type': JSON_MIME_TYPE}) # 201: Created
    

@app.route('/logout', methods=['POST'])
def logout():
    """Logs the user out."""
    # Get the json data posted by the user
    data = request.json
    
    if not data.get('access_token'):
        # Error: Cannot have missing data
        error = json.dumps({'error': 'Missing field/s (access_token)'})
        return json_response(error, 401) # 401: Unauthorized
    
    # Delete the user's access token
    delete_query = 'DELETE FROM auth WHERE access_token=:access_token;'
    g.db.execute(delete_query, {'access_token': data.get('access_token')})
    g.db.commit()
    
    return json_response(status=204) # 204: No Content


@app.route('/profile/<username>')
def get_profile(username):
    """Gets the profile is a specific user."""
    
    # Get the user's info
    user_query = 'SELECT * FROM user WHERE username=:username;'
    cursor = g.db.execute(user_query, {'username': username})
    user_data = cursor.fetchone()
    
    if not user_data:
        # The user does not exist
        abort(404)
    
    # Get the user's tweets
    tweet_query = 'SELECT * FROM tweet WHERE user_id=:user_id;'
    cursor = g.db.execute(tweet_query, {'user_id': user_data[0]})
    tweet_data = cursor.fetchall()
    
    # Store the user's info and tweets in a dictionary
    data = {
        'user_id': user_data[0],
        'username': username,
        'first_name': user_data[3],
        'last_name': user_data[4],
        'birth_date': user_data[5],
        
        'tweets': [ {
            'date': python_date_to_json_str(sqlite_date_to_python(tweet[2])), 
            'id': tweet[0], 
            'text': tweet[3], 
            'uri': '/tweet/{}'.format(i)
        } for i, tweet in enumerate(tweet_data, 1) ],
        
        'tweet_count': len(tweet_data)
    }
    
    # Serialize the data as a json formatted stream
    json_content = json.dumps(data)
    
    return make_response(json_content, 200, {'Content-Type': JSON_MIME_TYPE})


@app.route('/profile', methods=['POST'])
@json_only
@auth_only
# The user_id variable is needed because the auth_only decorator adds a 'user_id'
# key (in addition to a value) to kwargs before returning the function.
def post_profile(user_id):
    """Updates the user's profile. Must be the authorized user."""
    # Get the json data posted by the user
    data = request.json
    
    if not all([data.get('first_name'), data.get('last_name'), data.get('birth_date')]):
        # Error: Cannot have missing data
        error = json.dumps({'error': 'Missing field/s (first_name, last_name, birth_date)'})
        return json_response(error, 400) # 400: Bad Request
        
    if not data.get('access_token'):
        # Error: The access token is missing
        error = json.dumps({'error': 'Missing Access Token'})
        return json_response(error, 401) # 401: Unauthorized
    
    # Update the user's info
    query = """UPDATE user 
               SET first_name=:first_name, last_name=:last_name, birth_date=:birth_date 
               WHERE id=:user_id;"""
    query_args = {
        'first_name': data.get('first_name'),
        'last_name': data.get('last_name'),
        'birth_date': data.get('birth_date'),
        'user_id': user_id
    }
    g.db.execute(query, query_args)
    g.db.commit()
    
    return json_response(status=202) # 202: Accepted


@app.route('/tweet/<int:tweet_id>', methods=['GET', 'DELETE'])
def get_or_delete_tweet(tweet_id):
    """Get a tweet or delete a tweet."""
    if request.method == 'GET':
        # Get the tweet data
        tweet_query = 'SELECT * FROM tweet WHERE id=:tweet_id;'
        cursor = g.db.execute(tweet_query, {'tweet_id': tweet_id})
        tweet = cursor.fetchone() # (tweet_id, user_id, date, content)
        
        if not tweet:
            # The tweet does not exist
            abort(404)
        
        # Get the username of the tweet
        user_query = 'SELECT username FROM user WHERE id=:user_id;'
        cursor = g.db.execute(user_query, {'user_id': tweet[1]})
        username = cursor.fetchone()

        if not username:
            # User does not exist
            abort(404)
        
        # Store the tweet info in a dictionary
        data = {
            'id': tweet[0],
            'content': tweet[3],
            'date': python_date_to_json_str(sqlite_date_to_python(tweet[2])),
            'profile': '/profile/{}'.format(username[0]),
            'uri': '/tweet/{}'.format(tweet_id)
        }
        
        # Serialize the data as a json formatted stream
        json_content = json.dumps(data)
        
        return make_response(json_content, 200, {'Content-Type': JSON_MIME_TYPE})
        
    if request.method == 'DELETE':
        # Get the json data posted by the user
        data = request.json
        
        access_token = data.get('access_token')
    
        if not access_token:
            # Error: The access token is missing
            error = json.dumps({'error': 'Missing Access Token'})
            return json_response(error, 401) # 401: Unauthorized
            
        # Check if the tweet exists
        tweet_query = 'SELECT * FROM tweet WHERE id=:tweet_id;'
        cursor = g.db.execute(tweet_query, {'tweet_id': tweet_id})
        if not cursor.fetchone():
            # Tweet does not exist
            abort(404)
            
        # Check for valid token
        token_query = 'SELECT * FROM auth WHERE access_token=:access_token;'
        cursor = g.db.execute(token_query, {'access_token': access_token})
        auth_info = cursor.fetchone()
        if not auth_info:
            # Invalid access token
            abort(401)
        
        # User ID of the provided access token. This user ID may be different 
        # from the user who posted the tweet we're trying to delete.
        user_id = auth_info[1]
        
        # Check that the user actually submitted the tweet they're trying to delete
        tweet_query = 'SELECT id FROM tweet WHERE user_id=:user_id;'
        cursor = g.db.execute(tweet_query, {'user_id': user_id})
        tweet_ids = cursor.fetchall()
        if not any([True for id in tweet_ids if tweet_id == id[0]]):
            # Invalid access token. Token is in the database, but it is 
            # associated with a different user.
            abort(401)
            
        # Delete the tweet
        delete_query = 'DELETE FROM tweet WHERE id=:tweet_id;'
        g.db.execute(delete_query, {'tweet_id': tweet_id})
        g.db.commit()
        
        return json_response(status=204) # 204: No Content


@app.route('/tweet', methods=['POST'])
@json_only
def post_tweet():
    """Post a tweet."""
    # Get the json data posted by the user
    data = request.json
    
    if not data.get('content'):
        # Error: Cannot have missing data
        error = json.dumps({'error': 'Missing field/s (content)'})
        return json_response(error, 400) # 400: Bad Request

    if not data.get('access_token'):
        # Error: The access token is missing
        error = json.dumps({'error': 'Missing Access Token'})
        return json_response(error, 401) # 401: Unauthorized
    
    # Check for valid token
    token_query = 'SELECT * FROM auth WHERE access_token=:access_token;'
    cursor = g.db.execute(token_query, {'access_token': data.get('access_token')})
    if not cursor.fetchone():
        # Invalid access token
        abort(401)
    
    # Get the user's id
    user_id_query = 'SELECT user_id FROM auth WHERE access_token=:access_token;'
    cursor = g.db.execute(user_id_query, {'access_token': data.get('access_token')})
    user_id = cursor.fetchone()
    
    if not user_id:
        # The user does not exist
        abort(404)
     
    # Insert the tweet into the database 
    tweet_query = """INSERT INTO tweet ('user_id', 'content') VALUES (?, ?);"""
    g.db.execute(tweet_query, (user_id[0], data.get('content')))
    g.db.commit()
    
    return json_response(status=201) # 202: Created



# @app.errorhandler(404)
# def not_found(e):
#     return '', 404


# @app.errorhandler(401)
# def bad_request(e):
#     return '', 401
