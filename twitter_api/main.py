import sqlite3

from flask import Flask
from flask import g, abort, request, jsonify
import json
from werkzeug.wrappers import Response
from utils import *
from datetime import *

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


@app.route('/login', methods=['POST'])
def login():
    if request.method == "POST":
        try:
            username = request.json['username']
        except:
            abort(404)
        try:
            password = request.json['password']
        except:
            abort(400)

        cursor = g.db.execute('SELECT * FROM user WHERE username=?',(username,))
        user = cursor.fetchone()
        if user == None:
            abort(404)
        if user[2] != md5(password).hexdigest():
            abort(401)
        if user != None:
            access_token = make_uid()
            cursor = g.db.execute("SELECT id FROM user WHERE username=?",(username,))
            user_id = cursor.fetchone()
            g.db.execute('INSERT INTO auth ("user_id", "access_token") VALUES (?,?)',(user_id[0], access_token))
            g.db.commit()
            return jsonify({"access_token": access_token}), 201

            

#PYTHONPATH= py.test tests/resources_tests/test_login.py::LoginResourceTestCase::test_login_successful

@app.route('/logout', methods=['POST'])
def logout():
    if request.method == 'POST':
        # if access token is passed
        try:
            access_token = request.json['access_token']
        except:
            abort(401)
        # test if access token exists
        cursor = g.db.execute('SELECT * FROM auth WHERE access_token=?',(access_token,))
        user_id = cursor.fetchone()
        if user_id != None:
            g.db.execute('DELETE FROM auth WHERE access_token=?',(access_token,))
            g.db.commit()
            return "okay", 204
        else:
            abort(400)
            
            

@app.route('/profile/<username>')
def profile(username):
    
    cursor = g.db.execute('SELECT * FROM user WHERE username=?',(username,))
    profile = cursor.fetchone()
    if profile:
        
        data = {
            'user_id': profile[0],
            'username': profile[1],
            'first_name': profile[3],
            'last_name': profile[4],
            'birth_date': profile[5],
            'tweets': [],
            'tweet_count': 0
        }
        
        tweets_cursor = g.db.execute('SELECT * FROM tweet WHERE user_id=?', (profile[0],))
        tweets = tweets_cursor.fetchall()
        print(tweets)
        
        data['tweet_count'] = len(tweets)
        for tweet in tweets:
            data['tweets'].append({
                'date': tweet[2],
                'id': tweet[0],
                'text': str(tweet[3]),
              'uri': '/tweet/{}'.format(tweet[0])
            })
        return jsonify(data)
    else:
        abort(404)

@app.route('/profile', methods=["POST"])
@json_only
@auth_only
def update_profile():
    required_fields = ['first_name', 'last_name', 'birth_date']
    for field in required_fields:
        if field not in request.json:
            abort(400)
            
    update_profile_sql = '''
        UPDATE user 
        SET first_name='{}', last_name='{}', 'birth_date'='{}'
        '''.format(request.json['first_name'], request.json['last_name'], request.json['birth_date'])
    g.db.execute(update_profile_sql)
          
    g.db.commit()
    return '', 201
    
@app.route('/tweet/<tweet_id>')
def get_tweet(tweet_id):
    
    tweet_cursor = g.db.execute("SELECT * FROM tweet WHERE id=?",(tweet_id,))
    tweet = tweet_cursor.fetchone()
    print(tweet)
    if not tweet:
        abort(404)

    tweeter_cursor = g.db.execute("SELECT * FROM user WHERE id=?",(tweet[1],))
    tweeter = tweeter_cursor.fetchone()
    # sample tweet (1, 1, u'2016-06-01 05:13:00', u'Tweet 1 testuser1')
    data = {
        'id': tweet[0],
        'content': tweet[3],
        'date': tweet[2],
        'profile': '/profile/{}'.format(tweeter[1]),
        'uri': '/tweet/{}'.format(tweet[0])
    }
    return Response(json.dumps(data), content_type=JSON_MIME_TYPE)
    
@app.route('/tweet', methods=['POST'])
@json_only
@auth_only
def post_tweet():
    if 'content' not in request.json:
        abort(401)
    
    content = request.json['content']
    access_token = request.json['access_token']
    
    cursor = g.db.execute('SELECT user_id FROM auth WHERE access_token=?',(access_token,))
    user_id = cursor.fetchone()[0]
    g.db.execute("INSERT INTO tweet (user_id, content) VALUES (?,?)", (user_id, content,))
    g.db.commit()
    return '', 201

@app.route('/tweet/<tweet_id>', methods=['DELETE'])
@auth_only
def delete_tweet(tweet_id):
    access_token = request.json['access_token']
    tweet = g.db.execute("SELECT * FROM tweet WHERE id=?",(tweet_id, )).fetchone()
    
    if not tweet:
        abort(404)
        
    requester_user_id = g.db.execute('SELECT user_id FROM auth WHERE access_token=?',(access_token, )).fetchone()[0]
    tweet_owner_user_id = tweet[1]

    if requester_user_id != tweet_owner_user_id:
        abort(401)
        
    g.db.execute("DELETE FROM tweet WHERE id=?",(tweet_id,))
    g.db.commit()
    return '', 204
