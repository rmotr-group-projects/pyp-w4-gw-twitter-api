import sqlite3
import json
from flask import Flask, Response, request, abort
from flask import g

# extra modules we added
from hashlib import md5
import random
from .utils import JSON_MIME_TYPE, auth_only, json_only
import string
from datetime import datetime

app = Flask(__name__)
#api = Api(app)

def connect_db(db_name):
    return sqlite3.connect(db_name)

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])
    users = g.db.execute('SELECT access_token FROM auth')
    
# implement your views here
@app.route('/login', methods = ['POST'])
@json_only
def login():
    data = request.get_json()
    try:
        post_username = data['username']
        post_password = data['password']
    except KeyError:
        abort(400) # Bad request
    
    sql_command = 'SELECT username, password, id FROM user WHERE username = ?'
    
    found_user_cursor = g.db.execute(sql_command, [post_username])
    found_user = found_user_cursor.fetchone()
    try:
        username, password, id = found_user
    except TypeError: # if username did find a match in db
        abort(404) # Not found
        
    post_password = post_password.encode('utf-8') # needs to be in bytes
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

    post_request = request.get_json()
    post_access_token = post_request['access_token']

    # Delete entire row from auth table
    sql_command = 'DELETE FROM auth WHERE access_token = ?'
    g.db.execute(sql_command, [post_access_token])
    g.db.commit()
    return ('', 204) # No Content
    
@app.route('/tweet/<tweet_id>')
def get_tweet(tweet_id):

    # sql_command = 'SELECT * FROM tweet WHERE id = ?'
    # tweet_cursor = g.db.execute(sql_command, [tweet_id])
    # tweet = tweet_cursor.fetchone()
    # if not tweet:
    #     abort(404)
    
    post_tweet_id, post_user_id, post_created, post_content = get_tweet_info(tweet_id)
    
    # if request.method == 'POST': # want to delete tweet
    #     # need to get token...
    #     # kinda sucks - rewriting utils.py (why restful-flask is better...
    #     # we could have separate )
    #     post_request = request.get_json()
    #     if request.get_json() is None:
    #         abort(400) # Bad request
    #     post_access_token = post_request['access_token']
    
    uri = '/tweet/{}'.format(post_tweet_id)
    
    # need to get username
    sql_command = 'SELECT username FROM user WHERE id = ?'
    user_cursor = g.db.execute(sql_command, [post_user_id])
    user_tuple = user_cursor.fetchone()
    username = user_tuple[0]
    profile = '/profile/{}'.format(username)
    
    # need to convert date 
    # AssertionError: u'2016-06-01 05:13:00' != '2016-06-01T05:13:00'
    post_created_dt = datetime.strptime(post_created, "%Y-%m-%d %H:%M:%S")
    post_created_st = post_created_dt.strftime("%Y-%m-%dT%H:%M:%S")
    return_dict = dict(id=post_tweet_id, content=post_content,
                    date=post_created_st, profile=profile, uri=uri)
    response = Response(
        json.dumps(return_dict), status=200, content_type=JSON_MIME_TYPE)
    return response
    
def get_tweet_info(tweet_id):
    # returns all info about tweet based on tweet id
    # tweet_id, user_id, created, content
    sql_command = 'SELECT * FROM tweet WHERE id = ?'
    tweet_cursor = g.db.execute(sql_command, [tweet_id])
    tweet = tweet_cursor.fetchone()
    if not tweet:
        abort(404)
    return tweet
    
def _get_user_id_from_token(request):
    access_token = request.get_json()['access_token']
    sql_command = 'SELECT user_id FROM auth WHERE access_token = ?'
    user_id_cursor = g.db.execute(sql_command, [access_token])
    return user_id_cursor.fetchone()[0]
    
@app.route('/tweet/<tweet_id>', methods = ['DELETE'])
@json_only
@auth_only
def delete_tweet(tweet_id):
    tweet_user_id = get_tweet_info(tweet_id)[1]
    
    # we know access_token is good, so get the client_user_id
    client_user_id = _get_user_id_from_token(request)
    
    if tweet_user_id != client_user_id:
        abort(401)
        
    # Delete entire row from tweet table
    sql_command = 'DELETE FROM tweet WHERE id = ?'
    g.db.execute(sql_command, [tweet_id])
    g.db.commit()
    return ('', 204) # No Content
    
@app.route('/tweet', methods = ['POST'])
@json_only
@auth_only
def create_tweet():
    content = request.get_json()['content']
    client_user_id = _get_user_id_from_token(request)
    
    sql_command = 'INSERT INTO tweet (user_id, content) VALUES (?, ?)'
    g.db.execute(sql_command, [client_user_id, content])
    g.db.commit()
    
    return ('Created', 201)
    
        
'''
DROP TABLE if exists tweet;
CREATE TABLE tweet (
  id INTEGER PRIMARY KEY autoincrement,
  user_id INTEGER,
  created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  content TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES user(id),
  CHECK(
      typeof("content") = "text" AND
      length("content") <= 140
  )
'''

@app.errorhandler(404) # Not found
def not_found(e):
    return '', 404

@app.errorhandler(401) # Unauthorized
def not_found(e):
    return '', 401

@app.errorhandler(400) # Bad request
def not_found(e):
    return '', 400

@app.route('/profile/<username>')
def profile(username):
    # sql_command = 'SELECT * FROM user WHERE username = ?'
    # user_cursor = g.db.execute(seq_command, [username])
    # user_tuple = user_cursor.fetchone()
    # labels = ("user_id", "username", "first_name", "last_name", "birth_date")
    # profile_dict = dict(zip(labels, user_tuple))
    
    
    profile_json_data = None
    sql_command1 = 'SELECT id, username, first_name, last_name, birth_date FROM user WHERE username = ?'
    user_db_data = g.db.execute(sql_command1, [username])
    user_data = user_db_data.fetchone()
    try:
        user_id = user_data[0]
    except TypeError:
        abort(404)
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
        x = row_dict['date']
        x = datetime.strptime(x, "%Y-%m-%d %H:%M:%S")
        x = x.strftime("%Y-%m-%dT%H:%M:%S")
        row_dict['date'] = x
        tweet_list.append(row_dict)

    profile_json_data['tweet'] = tweet_list
    profile_json_data['tweet_count'] = len(tweet_list)
    response = Response(
        json.dumps(profile_json_data), status=200, content_type=JSON_MIME_TYPE)
    return response
# http://twitter-api-davidgranas.c9users.io:8080/profile/demo    

@app.route('/profile', methods = ['POST'])
@json_only
@auth_only
def profile_update():
    data = request.get_json()
    #if not session.get('logged_in'): #http://flask.pocoo.org/docs/0.11/tutorial/views/
    #    abort(401)
    try:
        #how to handle situation where data does not contain a value for a field?
        new_firstname = data['first_name']
        new_lastname = data['last_name']
        new_birthdate = data['birth_date']
    except KeyError:
        abort(400)
        
    client_user_id = _get_user_id_from_token(request)
    sql_command = 'UPDATE user SET first_name = ?, last_name = ?, \
        birth_date = ? WHERE id = ?'
    sql_args = [new_firstname, new_lastname, new_birthdate, client_user_id]
    g.db.execute(sql_command, sql_args)
    g.db.commit()
    return ('', 201)
    '''
    data = {
            "access_token": self.user1_token,
            "first_name": "New name",
            "last_name": "New last name",
            "birth_date": "1988-01-01",
        }
        if request.method == 'POST':
        try: # update the user profile
            new_username = request.form['username']
            new_firstname = request.form['first_name']
            new_lastname = request.form['last_name']
            new_birthdate = request.form['birth_date']
            sql_command = 'UPDATE user SET username = ?, first_name = ?, \
            last_name = ?, birth_date = ? WHERE id = ?'
            sql_args = [new_username, new_firstname, new_lastname, 
            new_birthdate, session['user_id']]
            g.db.execute(sql_command, sql_args)
            g.db.commit()
            
            flash('Your profile was correctly updated')
        except:
            flash('Your profile was not updated')
    '''
