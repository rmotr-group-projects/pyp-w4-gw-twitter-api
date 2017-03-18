import sqlite3

from flask import Flask, g, request, url_for, Response, abort
import json
from .utils import *
from hashlib import md5
import string
import random

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here

@json_only
@app.route('/login', methods = ['POST'])
def login():    # jon working on
    # Inputs: username and password
    # Ouputs: generated new access token for given username.
    authdata = request.get_json()
    
    try:
        username = authdata['username']
        password = authdata['password']
        password = password.encode('utf-8')
        password = md5(password).hexdigest()
    except KeyError:
        abort(400)

    db_authdata = g.db.execute('SELECT password, id from user WHERE username = ?', (username,))
    pass_and_id = db_authdata.fetchone()
    if pass_and_id:
        passdata, uid = pass_and_id
    else:
        passdata = None
        
    if not passdata: # no entry in DB.  should be 400, but tests asks for 404.
        abort(404)
    
    if passdata != password:
        abort(401)
    
    usertoken = generate_token()
    
    g.db.execute('INSERT INTO auth (user_id, access_token) VALUES (?, ?)', (uid, usertoken))
    g.db.commit()
    
    return Response(json.dumps(dict(access_token = usertoken)), status=201, content_type=JSON_MIME_TYPE)


@auth_only
@json_only
@app.route('/logout', methods = ['POST'])
def logout(): # Prashant is trying this now
    uid = token_to_uid(request)
    g.db.execute('DELETE FROM auth WHERE user_id = ?', (uid,))
    g.db.commit()
    return Response('', status=204)


@app.route('/profile/<username>', methods = ['GET'])
def read_profile(username):
    # go look for profile in DB. 
    profile = fetch_profile(username)
    # no profile: 404
    if not profile:
        abort(404)
    
    uid, username, first_name, last_name, birth_date = profile
    
    # format of this: tests/test_profile_resource.py line 14.
    profile_dict = {
        'user_id': uid,
        'username': username,
        'first_name': first_name,
        'last_name': last_name,
        'birth_date': birth_date
    }
    tweets = fetch_user_tweets(uid)
    profile_dict['tweet'] = tweets
    profile_dict['tweet_count'] = len(tweets)
    # 200 code in Response for success.
    # return the profile, plus the tweets as a big dict, json encoding
    return Response(json.dumps(profile_dict), status=200, content_type=JSON_MIME_TYPE)
    

@app.route('/profile', methods = ['POST'])
@json_only
@auth_only
def write_profile():
    # snarf profile from json
    profile = request.get_json()
    
    # check for all the required values 
    # see: "test_post_profile_missing_required_fields"
    try:
        first_name = profile['first_name']
        last_name = profile['last_name']
        birth_date = profile['birth_date']
        newdata = (first_name,last_name,birth_date)
    except (TypeError, KeyError):
        abort(400)

    uid = token_to_uid(request)
    g.db.execute('UPDATE user SET first_name = ?, last_name = ?, birth_date = ?', newdata)
    g.db.commit()
    return Response('', 201)


@json_only
@auth_only
@app.route('/tweet', methods = ['POST'])
def new_tweet():
    
    uid = token_to_uid(request)
    g.db.execute('INSERT INTO tweet (user_id, content) VALUES (?, ?)', (uid, request.get_json()['content']))
    g.db.commit()
    return Response('', 201)

@app.route('/tweet/<tweet_id>', methods = ['GET']) # lana
def read_tweet(tweet_id):
    tweet_data = g.db.execute('SELECT id, user_id, created, content FROM tweet where id=?', [tweet_id]).fetchone()
    if not tweet_data: # test_get_tweet_by_id_doesnt_exist
        abort(404)
        
    tweet_id, uid, created, content = tweet_data
    username = g.db.execute('SELECT username from user WHERE id=?', [uid]).fetchone()[0]
    
    response_dict = {
        "id": tweet_id,
        "content": content,
        "date": created,
        "profile": '/profile/{}'.format(username),
        "uri": '/tweet/{}'.format(tweet_id)
    }
    
    return Response(json.dumps(response_dict), status=200, content_type=JSON_MIME_TYPE)

@json_only
@auth_only
@app.route('/tweet/<tweet_id>', methods = ['DELETE'])
def delete_tweet(tweet_id):
    # given tweet id, look up the tweet in the tweets table and delete it
    # only allow user to delete own tweets.
    
    # uid from the request
    uid = token_to_uid(request) 
    # uid from db for this tweet id.
    tweet_data = g.db.execute('SELECT * FROM tweet WHERE id = ?', (tweet_id,))

    try:
        tweet_uid = tweet_data.fetchone()[0]
    except (KeyError, TypeError):
        abort(404)
        
    if uid is not tweet_uid:
        abort(401)
        
    g.db.execute('DELETE from tweet WHERE id = ?', (tweet_id,))
    g.db.commit()
    return Response('', 204)


# helper functions below here
@json_only
def token_to_uid(request): # jon
    # returns a username given a token
    if 'access_token' not in request.get_json():
        abort(401)
    else:    
        token = request.get_json()['access_token']

    uid_results = g.db.execute('SELECT user_id FROM auth WHERE access_token = ?', (token,))
    uid = uid_results.fetchone()
    if uid:
        return uid[0]
    else:
        abort(401)


def fetch_profile(username): # jon
    # fetch the user's profile from the DB.
    profile_data = g.db.execute(
        'SELECT id, username, first_name, last_name, birth_date FROM user WHERE username = ?', 
        (username,)
    )
    return profile_data.fetchone()

def fetch_user_tweets(user_id): # jon
    # fetch all of the users's tweets, returns as a list of dicts.
    alltweets = g.db.execute('SELECT id, created, content FROM tweet WHERE user_id = ?', (user_id,))
    # need to push this into a dict now.
    results = []
    for tweet in alltweets:
        tweet_id, created, content = tweet
        # this is the format from the profile test.
        #    'date': '2016-06-01T05:13:00',
        #    'id': 1,
        #    'text': 'Tweet 1 testuser1',
        #    'uri': '/tweet/1'
        formatted_tweet = {
            'id': tweet_id,
            'date': created, # i hope i don't have to mess with date!
            'text': content,
            'uri': '/tweet/{}'.format(tweet_id)
        }
        results.append(formatted_tweet)
    return results # a list of dicts, each dict a discreet tweet
        
def generate_token():  # jon
    # IDEA CREDIT: http://davidsj.co.uk/blog/python-generate-random-password-strings/
    #chars = string.ascii_letters + string.digits
    chars = string.ascii_letters + string.digits + string.punctuation
    pwdSize = 20
    return  ''.join((random.choice(chars)) for x in range(pwdSize))

# pre-written handlers.  wrapped in Response.
@app.errorhandler(404)
def not_found(e):
    return Response('', 404)


@app.errorhandler(401)
def not_found(e):
    return Response('', 401)
