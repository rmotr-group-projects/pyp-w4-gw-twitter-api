import sqlite3

from flask import Flask
from flask import g, request, abort, jsonify, make_response
from . utils import md5
import binascii, os, json
from datetime import datetime
# from functools import update_wrapper

app = Flask(__name__)

def connect_db(db_name):
    db = sqlite3.connect(db_name)
    return db
    

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])

# http://pyp-w4-gw-twitter-api.vkotek.c9users.io/

# views
@app.route('/login', methods=['POST'])
def login():
    if request.method != 'POST':
        abort(401)
        
    data = request.get_json()
        
    if not 'username' in data or data['username'] == None:
        abort(404)
        
    if not 'password' in data or data['password'] == None:
        abort(400)
        
    user = g.db.execute('SELECT id, username, password FROM user WHERE username == ?',
        [data['username']])
        
    user = user.fetchone()

    if not user:
        abort(404)
    
    if user[2] != md5(data['password']).hexdigest():
        print('Incorrect pass.')
        abort(401)
    print('{} matches.'.format(data['password']))
    
    token = binascii.hexlify(os.urandom(16))
    
    response = make_response(jsonify(access_token=token), 201)
    
    # auth_exists = g.db.execute('SELECT user_id FROM auth WHERE user_id == ?', [user[0]])
    # if auth_exists:
    #     abort(401)
    
    g.db.execute('INSERT INTO auth ("user_id","access_token") VALUES (?, ?)',
    [user[0], token])
    g.db.commit()
    print("Created auth '{}' for user [{}] {}".format(token, user[0], user[1]))
    return response

# PYTHONPATH=. py.test tests/resources_tests/test_login.py::LoginResourceTestCase::test_login_successful
# PYTHONPATH=. py.test tests/resources_tests/test_profile_resource.py::ProfileResourceTestCase::test_post_profile_content_not_json

@app.route('/logout', methods=['POST'])
def logout():
    data = request.get_json()
    if 'access_token' not in data:
        abort(401)
    g.db.execute('DELETE FROM auth WHERE access_token == ?',
    [data['access_token']])
    g.db.commit()
    return '', 204

@app.route('/profile/<user>')
def user_profile(user):
    
    # get user's info
    user = g.db.execute('SELECT id, username, first_name, last_name, birth_date FROM user WHERE username == ?', [user])
    user = user.fetchone()
    if not user:
        abort(404)
        
    # get tweet ids of user
    tweets = get_tweets(user[0])
    print(tweets)
    
    response = jsonify(
        user_id = user[0],
        username = user[1],
        first_name = user[2],
        last_name = user[3],
        birth_date = user[4],
        tweets = tweets,
        tweet_count = len(tweets)
    )
    
    print(response)
    
    return make_response(response, 200)

@app.route('/profile', methods=['GET','POST'])
def profile():
    
    # This could be a decorator but couldn't get it working because:
    # (Overwriting existing endpoint function error)
    if request.headers['Content-Type'] != 'application/json':
        abort(400)
      
    if request.method == 'POST': 
        data = request.get_json()
        
        # Request is missing access token
        if 'access_token' not in data:
            abort(401)
        
        user_id = g.db.execute('SELECT user_id FROM auth WHERE access_token == ?',
            [data['access_token']])
        user_id = user_id.fetchone()
        
        # Access token invalid (not found in DB)
        if not user_id:
            abort(401)
        
        required_fields = ['first_name','last_name','birth_date']
        if not all([field in data for field in required_fields]):
            abort(400)
        
        g.db.execute('UPDATE user SET\
            first_name = ?,\
            last_name = ?,\
            birth_date = ? \
            WHERE id == ?',[
            data['first_name'],
            data['last_name'],
            data['birth_date'],
            user_id[0]])
        g.db.commit()
        
        x = g.db.execute('SELECT * FROM user WHERE id = ?', [user_id[0]])
        print(x)
        x = x.fetchone()
        print(x)
        
    return 'Profile updated successfully', 201
    


# errors handlers

@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401

# https://twitter-api-vkotek.c9users.io/



def get_tweets(user_id):
    
    tweets = g.db.execute('SELECT id, content, created FROM tweet WHERE user_id == ?', [user_id])
    
    response = [{
        'date': datetime.strptime(tweet[2], '%Y-%m-%d %H:%M:%S').isoformat(),
        'id': tweet[0],
        'text': tweet[1],
        'uri': '/tweet/{}'.format(tweet[0]) } for tweet in tweets.fetchall()]

    return response