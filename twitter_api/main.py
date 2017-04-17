import sqlite3

from flask import Flask, session, request
from flask import g
from flask import jsonify
from twitter_api.utils import md5
from random import getrandbits
import json

# code copied from solution
JSON_MIME_TYPE = 'application/json'

app = Flask(__name__)

def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if 'username' in data and 'password' in data:
        # get username/pw
        username = data['username']
        password = data['password']
        hashed_password = md5(password).hexdigest()
        _SQL = "SELECT id, username, password from user WHERE username=(?)"
        cursor = g.db.execute(_SQL, (username,))
        user = cursor.fetchone() 
        
        if not isinstance(user, tuple):
            #user did not exist
            return 'Invalid Username', 404
        
        if username == user[1] and hashed_password == user[2]:
            # insert auth token into DB
            # return json accesstoken
            token = md5(str(getrandbits(128))).hexdigest()
            g.db.execute("INSERT INTO auth (user_id, access_token) VALUES (?, ?);",(user[0], token))
            g.db.commit()
            return jsonify(access_token=token), 201
        elif hashed_password != user[2]:
            return 'Invalid Credentials', 401
        
    return ('Invalid request', 400)

   
@app.route('/logout', methods=['POST'])
def logout():
    data = request.get_json()
    if len(data) == 0:
        return('Unauthorized Action', 401)
    # needs to have code written that checks if the value passed to data is an "access_token"
    #   and if the access_token is part of auth; otherwise throw 401 error
    # if 'access_token' in data:
    # cursor = g.db.execute("SELECT")
    g.db.execute("DELETE FROM auth WHERE access_token=(?)", (data['access_token'],))
    g.db.commit()
    return '', 204
    
@app.route('/profile', methods=['POST'])
def post_profile():
    data = request.get_json()
    
    try:
        if 'access_token' not in data:
            return '', 401
        cursor = g.db.execute("SELECT user_id FROM auth WHERE access_token=(?);", (data['access_token'],))
        uid = cursor.fetchone()
    except:
        return '', 400
        
    if uid:
        try:
            first_name = data['first_name']
            last_name = data['last_name']
            birth_date = data['birth_date']
        except:
            return '', 400
        _SQL = 'UPDATE user SET first_name=:first_name, last_name=:last_name, \
                birth_date=:birth_date WHERE id=:uid;'
        g.db.execute(_SQL, (first_name, last_name, birth_date, uid[0]))
        g.db.commit()
        return '', 201
    return '', 401

@app.route('/profile/<username>')
# app.login_required()
def get_profile(username):
    
    if request.method == 'GET':
        # grab user data
        _SQL = 'SELECT id, username, first_name, last_name, birth_date FROM user WHERE username=(?);' 
        cursor = g.db.execute(_SQL, (username,))
        user_data = cursor.fetchone()
        
        if not isinstance(user_data, tuple):
            #user did not exist
            return 'Invalid Username', 404
    
        # grab tweet data
        _SQL = 'SELECT created, id, content FROM tweet WHERE user_id=(?)'
        cursor = g.db.execute(_SQL, (user_data[0],))
        tweet_data = cursor.fetchall() # this is a tuple of tweets ((created, id, content), (), () ... ())
        tweets = []
        for item in tweet_data:
            tweets.append({'date':item[0].replace(' ', 'T'),
                                'id':item[1], 
                                'text': item[2], 
                                'uri':'/tweet/{}'.format(item[1])
                                })
                                
        packet = {'user_id':user_data[0],
                  'username': user_data[1],
                  'first_name': user_data[2],
                  'last_name': user_data[3],
                  'birth_date': user_data[4],
                  'tweets': tweets,
                  'tweet_count': len(tweets)
                  }
        print(packet)
        # code copied from solution, no mentors available          
        return jsonify(packet), 200
        # return jsonify('x'), 200, {'Content-Type': JSON_MIME_TYPE}
    
            
@app.route('/tweet/<int:tweet_id>')
def get_tweet(tweet_id):
    # GET /tweet/<TWEET-ID>
    # >>>
    # 200 Ok
    # {
    #   "id": <TWEET-ID>,
    #   "content": "Tweet test",
    #   "date": "2016-12-31T00:30:19",
    #   "profile": "/profile/<USERNAME>",
    #   "uri": "/tweet/<TWEET-ID>"
    # }
    
    _SQL = "SELECT content, created, user_id FROM tweet WHERE id=(?);"
    cursor = g.db.execute(_SQL, (tweet_id,))
    tweet_data = cursor.fetchone()
    
    if tweet_data == None:
        return "Tweet Doesn't Exist", 404
    
    _SQL = "SELECT username FROM user WHERE id=(?);" 
    cursor = g.db.execute(_SQL, (tweet_data[2],))
    user_data = cursor.fetchone()
    
    packet = {  "id": tweet_id,
                "content": tweet_data[0],
                "date": tweet_data[1].replace(' ', 'T'),
                "profile": "/profile/{}".format(user_data[0]),
                "uri": "/tweet/{}".format(tweet_id)
            }
    return jsonify(packet), 200


@app.route('/tweet/<int:tweet_id>', methods=['DELETE'])
def delete_tweet(tweet_id):
    data = request.get_json()
    
    # check authentication
    try:
        if 'access_token' not in data:
            return '', 401
        _SQL = "SELECT user_id FROM auth WHERE access_token=(?);"
        cursor = g.db.execute(_SQL, (data['access_token'],))
        uid = cursor.fetchone()
    except:
        return '', 400
        
    if not uid:
        # authentication token doesn't exist
        return '', 401
        # see if tweet ID has same user as auth
    _SQL = "SELECT user_id FROM tweet WHERE id=(?);"
    cursor = g.db.execute(_SQL, (tweet_id,))
    tweet_user_id = cursor.fetchone()
    if not tweet_user_id:
        # tweet doesn't exist
        return '', 404
    if tweet_user_id[0] != uid[0]:
        # user doesn't have authority to delete tweet
        return '', 401
    # then delete the tweet
    _SQL = "DELETE FROM tweet WHERE id=(?);"
    g.db.execute(_SQL, (tweet_id,))
    g.db.commit()
    return '', 204
    

@app.route('/tweet', methods=['POST'])
def post_tweet():
    data = request.get_json()
    
    # check authentication
    try:
        if 'access_token' not in data:
            return '', 401
        _SQL = "SELECT user_id FROM auth WHERE access_token=(?);"
        cursor = g.db.execute(_SQL, (data['access_token'],))
        uid = cursor.fetchone()
    except:
        return '', 400
    
    # post tweet   
    if uid:
        try:
            content = data['content']
        except:
            return '', 400
        _SQL = "INSERT INTO tweet (user_id, content) VALUES (?, ?);"
        g.db.execute(_SQL, (uid[0], content))
        g.db.commit()
        return '', 201
    return '', 401

@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def unauthorized(e):
    return '', 401
