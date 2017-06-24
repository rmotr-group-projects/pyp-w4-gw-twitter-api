import sqlite3

from flask import Flask
from flask import (g, request, session, redirect, jsonify, Response)
from uuid import uuid4
import json
from hashlib import md5

app = Flask(__name__)
CONTENT_TYPE= 'application/json'


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here
@app.route('/login', methods = ['POST'])
def login():
    json_data = request.get_json()
    
    if 'username' in json_data and 'password' in json_data:
        username = json_data['username']
        password = json_data['password']
        hash_password = md5(password.encode('utf-8')).hexdigest()
        cursor = g.db.execute("SELECT id, username, password FROM user WHERE username=:username",{'username':username})

        user_result = cursor.fetchone()
        
        if user_result is None:
            return 'Invalid username', 404
            
        _id, _username, _password = user_result
        
        if user_result and hash_password == _password:
            access_token = str(uuid4())
            g.db.execute('INSERT INTO auth (user_id, access_token) VALUES (:_id, :access_token)', {'_id': _id, 'access_token': access_token})
            g.db.commit()
            return json.dumps({'access_token':access_token}), 201
        else:
            return "wrong password", 401
    else:
        return "missing username or password", 400
            
@app.route('/logout', methods = ['POST'])
# @app.before_request
def logout():
    # if not request.get_json():
    #     return 'missing json', 400
    data = request.get_json()
    if 'access_token' not in data:
        return "missing token", 401
    
    user_token = request.get_json()['access_token']
    cursor = g.db.execute("select * from auth where access_token = :token;", {"token":user_token})
    result= cursor.fetchone()
    if result:
        g.db.execute("delete from auth where access_token = :token ", {"token":user_token})
        g.db.commit()
        return '', 204
    return '', 401



@app.route('/profile', methods=['POST'])
def profile():

    data = request.get_json()
    try:
        if 'access_token' not in data:
            return "missing token", 401
    except:
        return '', 400
    req_fields = ["access_token", 'first_name', "last_name","birth_date"]
    if not all([field in data for field in req_fields]):
        return 'missing fields!', 400
        
    access_token = data['access_token']
    
    cursor = g.db.execute("SELECT user_id FROM auth WHERE access_token = :token;", {"token":access_token})
    result = cursor.fetchone()
    
    if result is None:
        return 'No access token!', 401


    _userid = result[0]
    _first_name = data['first_name']
    _last_name = data['last_name']
    _birth_date = data['birth_date']
    _access_token = access_token
    
    g.db.execute("UPDATE user SET first_name = :first_name, last_name=:last_name, birth_date=:birth_date WHERE id=:id;", {'id':_userid, 'first_name':_first_name, 'last_name':_last_name, 'birth_date':_birth_date})
    g.db.commit()
    return 'all good', 201
    

    

@app.route('/profile/<username>', methods=['POST', 'GET'])
# @app.before_request
def profile_page(username):


    if request.method == 'GET':
        cursor = g.db.execute('SELECT id, username, first_name, last_name, birth_date FROM user WHERE username=:username',{'username':username})
        result_user = cursor.fetchone()
        
        if result_user is None:
            return 'Invalid username {}!'.format(username), 404
        
        _user_id, _username, _first_name, _last_name, _birth_date = result_user
            
        cursor = g.db.execute('SELECT id, created, content FROM tweet WHERE user_id = :user_id', {'user_id': _user_id})
        result_tweets = cursor.fetchall()
        tweets = []
        for twt in result_tweets:
            tweets.append({'id': twt[0], 'date': twt[1].replace(' ','T'), 'text': twt[2], 'uri': '/tweet/{}'.format(twt[0])})
        
        expected_results = {
            'user_id': _user_id,
            'username': _username,
            'first_name': _first_name,
            'last_name': _last_name,
            'birth_date': _birth_date,
            'tweets': tweets,
            'tweet_count': len(tweets)
        }    
        
        print (expected_results)
        return json.dumps(expected_results), 200, {'Content-Type': 'application/json'}
        


@app.route('/tweet/<tweetid>', methods = ['GET', 'DELETE'])
def tweet(tweetid):
    if request.method == 'DELETE':
        json_data = request.get_json()
        if json_data and 'access_token' in json_data:
            access_token = json_data['access_token']
            userid = g.db.execute("SELECT user_id FROM auth WHERE access_token=:access_token",{"access_token":access_token}).fetchone()
            if not userid:
                return 'not valid access token', 401
            check_id = g.db.execute("SELECT user_id FROM tweet WHERE id=:tweetid; ",{"tweetid":tweetid}).fetchone()
            if not check_id:
                return 'tweet doesnt exist', 404
            cursor = g.db.execute("SELECT user_id FROM tweet WHERE user_id=:userid and id=:tweetid; ",{"userid":userid[0], "tweetid":tweetid})
            sameuser = cursor.fetchone()
            if not sameuser:
                return 'tweet does not belong to you', 401
            g.db.execute("DELETE FROM tweet WHERE id=:tweetid;",{"tweetid":tweetid})
            g.db.commit()
            return 'deleted', 204
        else: 
            return 'not valid request', 401
    #GET REQUESTS
    cursor = g.db.execute("SELECT id, content, created, user_id FROM tweet WHERE id=:tweetid",{"tweetid":tweetid})
    queryresult = cursor.fetchone()
    if not queryresult:
        return "tweet doesn't exist", 404
    username = g.db.execute("SELECT username FROM user WHERE id=:userid",{"userid":str(queryresult[3])}).fetchone()[0]
    result = {"id":queryresult[0], "content":queryresult[1], "date":queryresult[2].replace(' ','T'), "profile":"/profile/"+username, "uri":"/tweet/"+str(tweetid)}
    return json.dumps(result), 200, {'Content-Type': 'application/json'}


@app.route('/tweet', methods = ['POST'])
def post_tweet():
    json_data = request.get_json()
    if not json_data or 'content' not in json_data:
      return "not valid json", 400
    if 'access_token' not in json_data:
        return 'no access token', 401
    access_token = json_data['access_token']
    check_token = g.db.execute("SELECT user_id FROM auth WHERE access_token=:access_token",{"access_token":access_token})
    res = check_token.fetchone()
    if not res:
        return 'not valid access token', 401
    content = json_data['content']
    g.db.execute("INSERT INTO tweet (user_id,content) VALUES (:user_id,:content);",{"user_id":res[0], "content":content})
    g.db.commit()
    return "success", 201


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
