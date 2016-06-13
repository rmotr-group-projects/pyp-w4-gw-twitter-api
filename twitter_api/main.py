import sqlite3
import random
from flask import Flask, Response, request, abort, g, jsonify
from .utils import JSON_MIME_TYPE, auth_only, json_only
from hashlib import md5
import json


app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here
@app.route('/login', methods = ['POST']) #require auth
@json_only
def login():  #no auth, auth token is issued here
    
    # takes in json with username / password
    login_data = request.get_json()
    try:
        username, password = login_data['username'], login_data['password']
    except:
        abort(400)
    
    # #check already logged in
    # query = 'SELECT user_id, access_token FROM auth WHERE access_token=?'
    # cursor = g.db.execute(query, (request.json['access_token']))
    # if cursor.fetchone():
    #     pass #
    # else:
    #     abort(401)    #already logged in because has access token
    
    query = 'SELECT password, id FROM user WHERE username = ?'    
    user_found_cursor = g.db.execute(query, [username])
    user_found = user_found_cursor.fetchone()
    
    if not user_found:
        abort(404) #user not found
    
    # compare passwords to make sure user is valid user logged in to right acc
    user_db_password, uid = user_found  #unpack db password, user id from db
    #md5 -need to encode user prov password
    if user_db_password != md5(password.encode(request.charset)).hexdigest():
        abort(401) #use not authorized
    
    
    # make (unsecure for now TODO fix make secure) access token
    noise = ''.join(["%s" % random.randint(0, 9) for num in range(0, 7)])
    user_access_token = str(uid) + noise
    # issues auth token -- generate and update database
    #username + 6 rand digits?
    sql_command = 'INSERT INTO auth (user_id, access_token) VALUES (?,?)'
    g.db.execute(sql_command, [uid, user_access_token])
    g.db.commit()
    
    # issues "201 ok" response AND returns dict of "access_token": <ACCESS-TOKEN>
    rv = dict(access_token = user_access_token)
    response = Response(json.dumps(rv), status=201, content_type=JSON_MIME_TYPE)
    
    return response
    #check that username exists
        #if so, check that pw matches db
        
    
@app.route('/logout', methods = ['POST'])
@json_only
@auth_only
def logout():
    query = 'DELETE FROM auth WHERE access_token=?'
    token = request.json['access_token']
    g.db.execute(query, (token,)) #
    g.db.commit()
    
    return Response("", 204)
    
@app.route('/profile/<username>', methods = ['GET']) #get public profile
def get_profile(username):

    # pull user db info passed on passed username 
    sql_query_username = 'SELECT id, username, first_name, last_name, birth_date FROM user WHERE username = ?'
    user_db_data = g.db.execute(sql_query_username, (username,))
    user_data = user_db_data.fetchone()
    
    if not user_data: #if no user data
        abort(404)
 
    #begin construction of dict to return
    profile_data = dict(zip(("user_id", "username", "first_name", "last_name", 
           "birth_date"), user_data))
           
    #query user tweets and then build tweet list
    sql_query_tweets = 'SELECT id, content, created FROM tweet WHERE user_id = ? ORDER BY id asc'
    user_tweets = g.db.execute(sql_query_tweets, (profile_data['user_id'],))

    # tweet_list = []
    # for tweet in user_tweets:
    #     row_dict = dict(zip("id", "text", "date", "uri", tweet))
    #     row_dict['uri'] = '/tweet/{}'.format(row_dict['uri'])
    #     #row_dict['date'] = formatdate(row_dict['date']) #still to do
    #     tweet_list.append(row_dict)
    tweet_list = [dict(id=row[0], text=row[1], date=row[2], uri="/tweet/" + str(row[0])) for row in user_tweets.fetchall()]
 
    profile_data['tweet'] = tweet_list
    profile_data['tweet_count'] = len(tweet_list)
    response = Response(
        json.dumps(profile_data), status=200, content_type=JSON_MIME_TYPE)
    return response



@app.route('/profile', methods = ['POST'])  #update  #require auth
@json_only
@auth_only
def update_profile():
    #get userid from auth based on access_token
    #if valid, post updated 
    new_info = set(['first_name', 'last_name', 'birth_date'])
    
    if new_info.intersection(request.json.keys()) != new_info:
        abort(400)
        
    if "access_token" not in request.json.keys():
        abort(401)
   
    try: 
        fn = request.json['first_name']
        ln = request.json['last_name']
        bd = request.json['birth_date']
        token = request.json['access_token']
    except:
        abort(400)
    
    cursor = g.db.execute("SELECT user_id FROM auth WHERE access_token=?", (token,))
    return_val = cursor.fetchone()
    user_id = return_val[0]
    
    g.db.execute("UPDATE user SET first_name=?, last_name=?, birth_date=? WHERE id=?", (fn, ln, bd, user_id))
    g.db.commit()
    return Response("", 201)

@app.route('/tweet/<tweet_id>')  #get
@json_only
@auth_only
def get_tweet(tweet_id):
           # get all the tweet info as well as username from user table
    sql_tweet_query = 'SELECT id, user_id, created, content FROM tweet WHERE id = ?'

    result_cursor = g.db.execute(sql_tweet_query, (tweet_id,))
    if not result_cursor.fetchone():
       abort(404)    
    #start to build the Response
    result_dict = zip(['id', 'user_id', 'date', 'text'], result_cursor.fetchone())

    sql_user_query = 'SELECT username FROM user WHERE id = ?'
    result_username = g.db.execute(sql_tweet_query, (result_dict['user_id'],))
    result_dict['profile'] = '/profile/{}'.format(result_username[0])
    result_dict['uri'] = '/tweet/{}'.format(tweet_id)

    response = Response(json.dumps(result_dict), status=200, content_type=JSON_MIME_TYPE)
    
    return response


@app.route('/tweet', methods = ['POST']) #post new tweet  #require auth
@json_only
@auth_only
def create_tweet():
    #check authorisation
    cursor = g.db.execute("SELECT user_id FROM auth WHERE access_token=?", (request.json['access_token'],))
    user_id = cursor.fetchone()
    content = request.json["content"]
    
    g.db.execute("INSERT INTO tweet (user_id, content) VALUES (?,?)", (user_id, content,))
    g.db.commit()
    
    return ("", 201)

@app.route('/tweet/<tweet_id>', methods = ['DELETE']) #delete tweet #require auth
@json_only
@auth_only
def delete_tweet(tweet_id):
    tweet_data = g.db.execute('SELECT * FROM tweet WHERE id = ?', (tweet_id,))
    if 'access_token' not in request.get_json():
        abort(401)
    else:    
        token = request.get_json()['access_token']

    uid_results = g.db.execute('SELECT user_id FROM auth WHERE access_token = ?', (token,))
    uid = uid_results.fetchone()[0]
    try:
        tweet_uid = tweet_data.fetchone()[0]
    except (KeyError, TypeError):
        abort(404)
        
    if uid is not tweet_uid:
        abort(401)
        
    g.db.execute('DELETE from tweet WHERE id = ?', (tweet_id,))
    g.db.commit()
    return Response('', 204)


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
