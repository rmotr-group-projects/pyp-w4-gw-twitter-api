import sqlite3
import json
from flask import Flask, Response, request, abort, url_for
from flask import g

# extra modules we added
from hashlib import md5
import random
from .utils import JSON_MIME_TYPE, auth_only, json_only
import string
from datetime import datetime

app = Flask(__name__)

def connect_db(db_name):
    return sqlite3.connect(db_name)

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])
    
# implement your views here
def _get_tweet_info(tweet_id):
    # returns (tweet_id, user_id, created, content)
    sql_command = 'SELECT * FROM tweet WHERE id = ?'
    tweet_cursor = g.db.execute(sql_command, [tweet_id])
    tweet = tweet_cursor.fetchone()
    if not tweet:
        abort(404)
    return tweet
    
def _get_user_id_from_token(request):
    # assumes access token has already been verified but can double check
    if 'access_token' not in request.get_json():
        abort(401)
    access_token = request.get_json()['access_token']
    sql_command = 'SELECT user_id FROM auth WHERE access_token = ?'
    user_id_cursor = g.db.execute(sql_command, [access_token])
    found_user = user_id_cursor.fetchone()
    if not found_user:
        abort(404)
    return found_user[0]
    
def _convert_date_iso_8601(created):
    dt_object = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
    return dt_object.strftime("%Y-%m-%dT%H:%M:%S")
    
@app.route('/login', methods = ['POST'])
@json_only
def login():
    data = request.get_json()
    
    if 'username' not in data:
        abort(400) # Bad request, no username
    elif 'password' not in data:
        abort(400) # Bad request, no password

    post_username = data['username']
    post_password = data['password']
    
    sql_command = 'SELECT password, id FROM user WHERE username = ?'
    
    found_user_cursor = g.db.execute(sql_command, [post_username])
    found_user = found_user_cursor.fetchone()
    if not found_user:
        abort(404) # Not found, username did find a match in db
    password, id = found_user
        
    post_password = post_password.encode(request.charset) # note from Santiago
    post_password = md5(post_password).hexdigest()
    
    if password != post_password:
        abort(401) # Unauthorized
        
    # generate access token
    char_list = string.ascii_lowercase + string.ascii_uppercase
    access_token = ''.join(random.choice(char_list) for _ in range(10))
    
    sql_command = 'INSERT INTO auth (user_id, access_token) VALUES (?, ?)'
    g.db.execute(sql_command, [id, access_token])
    g.db.commit()
    
    return_dict = dict(access_token = access_token)
    response = Response(
        json.dumps(return_dict), status=201, content_type=JSON_MIME_TYPE)
    return response
    
@app.route('/logout', methods = ['POST'])
@json_only
@auth_only
def logout():
    # Delete all entries for this user (they could have logged in multiple times)
    # good suggestion by Santiago
    user_id = _get_user_id_from_token(request)
    sql_command = 'DELETE FROM auth WHERE user_id = ?'
    g.db.execute(sql_command, [user_id])
    g.db.commit()
    return Response('', 204) # No Content
    
@app.route('/tweet/<tweet_id>')
def get_tweet(tweet_id):
    tweet_id, user_id, created, content = _get_tweet_info(tweet_id)
    uri = url_for('get_tweet', tweet_id = tweet_id) # good note from Santiago

    # get the username of who made that tweet
    sql_command = 'SELECT username FROM user WHERE id = ?'
    user_cursor = g.db.execute(sql_command, [user_id])
    user_tuple = user_cursor.fetchone()
    username = user_tuple[0]
    profile = url_for('profile', username = username)
    
    return_dict = dict(id=tweet_id, content=content,
                    date=_convert_date_iso_8601(created), 
                    profile=profile, uri=uri)
    response = Response(
        json.dumps(return_dict), status=200, content_type=JSON_MIME_TYPE)
    return response
    
@app.route('/tweet/<tweet_id>', methods = ['DELETE'])
@json_only
@auth_only
def delete_tweet(tweet_id):
    tweet_user_id = _get_tweet_info(tweet_id)[1]
    
    # we know access_token is good, so get the client_user_id
    client_user_id = _get_user_id_from_token(request)
    
    if tweet_user_id != client_user_id:
        abort(401)
        
    # Delete entire row from tweet table
    sql_command = 'DELETE FROM tweet WHERE id = ?'
    g.db.execute(sql_command, [tweet_id])
    g.db.commit()
    return Response('', 204) # No Content
    
@app.route('/tweet', methods = ['POST'])
@json_only
@auth_only
def create_tweet():
    content = request.get_json()['content']
    client_user_id = _get_user_id_from_token(request)
    
    sql_command = 'INSERT INTO tweet (user_id, content) VALUES (?, ?)'
    g.db.execute(sql_command, [client_user_id, content])
    g.db.commit()
    
    return Response('Created', 201)

@app.errorhandler(404) # Not found
def not_found(e):
    return Response('', 404)

@app.errorhandler(401) # Unauthorized
def not_found(e):
    return Response('', 401)

@app.errorhandler(400) # Bad request
def not_found(e):
    return Response('', 400)

@app.route('/profile/<username>')
def profile(username):

    #profile_json_data = None
    sql_command1 = 'SELECT id, username, first_name, last_name, birth_date FROM user WHERE username = ?'
    user_db_data = g.db.execute(sql_command1, [username])
    user_data = user_db_data.fetchone()
    
    if not user_data:
        abort(404)

    user_id = user_data[0]

    dict_keys = ("user_id", "username", "first_name", "last_name", 
            "birth_date")
    profile_json_data = dict(zip(dict_keys, user_data))

    # add tweets to the json_data dictionary
    sql_command2 = 'SELECT id, created, content, id FROM tweet WHERE user_id = ?'
    user_tweets = g.db.execute(sql_command2,[user_id])
    tweet_list = []
    for tweet in user_tweets:
        dict_keys = ("id", "date", "text", "uri")
        row_dict = dict(zip(dict_keys, tweet))
        row_dict['uri'] = '/tweet/{}'.format(row_dict['uri'])
        row_dict['date'] = _convert_date_iso_8601(row_dict['date'])
        tweet_list.append(row_dict)

    profile_json_data['tweet'] = tweet_list
    profile_json_data['tweet_count'] = len(tweet_list)
    response = Response(
        json.dumps(profile_json_data), status=200, content_type=JSON_MIME_TYPE)
    return response

@app.route('/profile', methods = ['POST'])
@json_only
@auth_only
def profile_update():
    data = request.get_json()
    if not all(key in data for key in ['first_name','last_name','birth_date']):
        abort(400) # missing values
        
    new_firstname = data['first_name']
    new_lastname = data['last_name']
    new_birthdate = data['birth_date']
        
    client_user_id = _get_user_id_from_token(request)
    sql_command = 'UPDATE user SET first_name = ?, last_name = ?, \
        birth_date = ? WHERE id = ?'
    sql_args = [new_firstname, new_lastname, new_birthdate, client_user_id]
    g.db.execute(sql_command, sql_args)
    g.db.commit()
    return Response('', 201)