import sqlite3

from flask import Flask
from flask import g, jsonify, abort, request, make_response
import binascii, os, json
from twitter_api import utils
from datetime import datetime



app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here
@app.route('/login', methods = ['POST'])
def login():
    data = request.get_json()
    
    if 'username' not in data:
        abort(404)
    
    if 'password' not in data:
        abort(400)
    
    password = utils.md5(data['password']).hexdigest()
    
    user = g.db.execute('select id,username,password from user where username=:username;', {'username': data['username']})
    
    fetch_user = user.fetchone()
    
    if fetch_user is None:
        abort(404)
    
    if fetch_user[1] != data['username']:
        abort(404)
    
    if fetch_user[2] != password:
        abort(401)
        
    
    token = binascii.hexlify(os.urandom(16)).decode('utf-8')
    response = make_response(jsonify(access_token=token),201)
    g.db.execute('insert into auth ("user_id", "access_token") values (:user_id, :token);', {'user_id': fetch_user[0], 'token': token})
    g.db.commit()
    
    return response
    
@app.route('/logout', methods=['POST'])  
def logout():
    data = request.get_json()
    token = data.get('access_token', None)
    if not token:
        abort(401)
    
    
    g.db.execute('DELETE FROM auth WHERE access_token=:token;', {'token': token})
    g.db.commit()
    
    return '', 204


@app.route('/profile/<username>', methods=['GET'])  
def profile(username):
    cursor1 = g.db.execute('select id,username,first_name,last_name,birth_date from user where username=:username;', {'username': username})
    user = cursor1.fetchone()
    
    if not user:
        abort(404)
    
    cursor2 = g.db.execute('select id,content,created from tweet where user_id=:user_id;', {'user_id':user[0]})
    tweets1 = cursor2.fetchall()
    
    response_tweets =[{
        'id': tweet[0],
        'text':tweet[1],
        'date': datetime.strptime(tweet[2], '%Y-%m-%d %H:%M:%S').isoformat(),
        'uri': '/tweet/{}'.format(tweet[0]) 
    }  for tweet in tweets1  ]

    response =jsonify(
        user_id = user[0],
        username = user[1],
        first_name = user[2],
        last_name = user[3],
        birth_date = user[4],
        tweets = response_tweets,
        tweet_count = len(tweets1)
        )
    
    return make_response(response,200)


@app.route('/profile', methods=['POST'])
@utils.json_only
@utils.auth_only
def post_profile():
        
    data = request.get_json()
    
    user_id = g.db.execute('select user_id from auth where access_token =:access_token;',{'access_token':data['access_token']})
    user_id = user_id.fetchone()
    
    if not user_id:
        abort(401)
    required_data =['first_name','last_name','birth_date']
    if not all([fields in data for fields in required_data]):
        abort(400)
    
    g.db.execute('update user set first_name=:first_name ,last_name=:last_name,birth_date=:birth_date where id=:user_id;',{'user_id': user_id[0],'first_name':data['first_name'],'last_name':data['last_name'],'birth_date':data['birth_date']})
    g.db.commit()
    
    return '', 201

@app.route('/tweet/<int:tweet_id>', methods=['GET'])
def get_tweet(tweet_id):
    
    cursor = g.db.execute("SELECT id,content,created,user_id FROM tweet WHERE id=:tweet_id;", {'tweet_id':tweet_id})
    tweet = cursor.fetchone()
    
    if not tweet:
        abort(404)
    
    cursor2 = g.db.execute("SELECT username FROM user WHERE id=:user_id;", {'user_id': tweet[3]})
    user = cursor2.fetchone()
    
    response_tweet = {
        'id': tweet[0],
        'content':tweet[1],
        'date': datetime.strptime(tweet[2], '%Y-%m-%d %H:%M:%S').isoformat(),
        'profile': "/profile/{}".format(user[0]),
        'uri': '/tweet/{}'.format(tweet[0])
    }

    response = jsonify(response_tweet)
    
    return make_response(response,200)


@app.route('/tweet', methods=['POST'])
@utils.json_only
@utils.auth_only
def post_tweet():
    
    data = request.get_json()
    
    user_id = g.db.execute("SELECT user_id FROM auth WHERE access_token=:access_token;", {'access_token': data['access_token']})
    user_id = user_id.fetchone()
    
    query = 'INSERT INTO tweet ("user_id", "content") VALUES (:user_id, :content);'
    params = {'user_id': user_id[0], 'content': data['content']}
    g.db.execute(query, params)
    g.db.commit()
    
    return "",201


@app.route('/tweet/<int:tweet_id>', methods=['DELETE'])
@utils.json_only
@utils.auth_only
def delete_tweet(tweet_id):
    
    data = request.get_json()
    
    cursor = g.db.execute("SELECT id,user_id FROM tweet WHERE id=:tweet_id;", {'tweet_id':tweet_id})
    tweet = cursor.fetchone()
    
    user_id = g.db.execute("SELECT user_id FROM auth WHERE access_token=:access_token;", {'access_token': data['access_token']})
    user_id = user_id.fetchone()
    
    if not tweet:
        abort(404)
    
    if user_id[0] != tweet[1]:
        abort(401)
    
    g.db.execute("DELETE FROM tweet WHERE id={};".format(tweet_id))
    g.db.commit()
    return "",204


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
