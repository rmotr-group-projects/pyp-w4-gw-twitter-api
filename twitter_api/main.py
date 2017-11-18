import sqlite3
import time

from os import urandom
from base64 import b64encode
from flask import Flask
from flask import g, request, jsonify, make_response
from twitter_api.utils import md5, json_only, auth_only

app = Flask(__name__)

def connect_db(db_name):
    return sqlite3.connect(db_name)

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


@app.route('/login', methods=['POST'])
@json_only
def login():
    data = request.get_json()
    
    if 'password' not in data:
        return 'Missing password', 400
    
    params = {
        'username': data['username'],
        'password': md5(data['password']).hexdigest()
    }
    cursor = g.db.execute('SELECT * FROM user WHERE username = :username AND password = :password;', params)
    user = cursor.fetchone()
    if user:
        # generate token
        random_bytes = urandom(64)
        access_token = b64encode(random_bytes).decode('utf-8')
        # insert into auth
        params = {'user_id' : user[0], 'access_token' : access_token}
        g.db.execute('INSERT INTO auth (user_id, access_token) VALUES (:user_id, :access_token);', params)
        g.db.commit()
        return (jsonify({'access_token': access_token}), 201)
    
    cursor = g.db.execute('SELECT * FROM user WHERE username = :username OR password = :password;', params)
    user = cursor.fetchone()
    if user[1] == params['username']:
        return 'Incorrect Password', 401
    else:
        return 'Username does not exists', 404

@app.route('/logout', methods=['POST'])
@json_only
def logout():
    data = request.get_json()
    
    if 'access_token' not in data:
        return '', 401
    
    params = {
        'access_token': data['access_token']
    }
    g.db.execute('DELETE FROM auth where access_token = :access_token;', params)
    g.db.commit()
    return '', 204
    
@app.route('/profile/<string:username>', methods=['GET'])
def get_profile(username):
    params = {'username' : username }

    cursor = g.db.execute("""
        SELECT u.id as user_id, u.username, u.first_name, u.last_name,
        u.birth_date, t.created, t.id, t.content
        FROM user u LEFT JOIN tweet t ON t.user_id = u.id
        WHERE u.username = :username;
    """, params)
    result = [dict(user_id=row[0], username=row[1], first_name=row[2], last_name=row[3],
                   birth_date=row[4], date=row[5], id=row[6], text=row[7])
               for row in cursor.fetchall()]
     
    if result:
        tweets = []
        if result[0]['date']:
            tweets = [dict(date=item['date'].replace(' ', 'T'), id=item['id'], 
                           text=item['text'], uri='/tweet/{}'.format(item['id'])) 
                     for item in result]
        data = dict(user_id=result[0]['user_id'], username=result[0]['username'], first_name=result[0]['first_name'], 
                      last_name=result[0]['last_name'], birth_date=result[0]['birth_date'],
                      tweets=tweets, tweet_count=len(tweets))
    
        return (jsonify(data), 200)
    else:
        return "Username does not exists", 404
        
@app.route('/profile', methods=['POST'])
@json_only
@auth_only
def post_profile():
    data = request.get_json()
    
    if 'first_name' not in data:
        return 'Missing first name', 400
    
    cursor = g.db.execute('SELECT user_id FROM auth WHERE access_token = :access_token', 
                            { 'access_token' : data['access_token'] })
    auth = cursor.fetchone()

    params = {
        'user_id' : auth[0],
        'first_name' : data['first_name'],
        'last_name' : data['last_name'],
        'birth_date' : data['birth_date']
    }
    g.db.execute('UPDATE user SET first_name = :first_name, last_name = :last_name, birth_date = :birth_date '\
                  'WHERE id = :user_id', params)
    g.db.commit()
    return 'Update profile completed', 202

@app.route('/tweet/<int:id>', methods=['GET', 'DELETE'])
@auth_only
def get_tweet(id):
    param = {'id' : id}
    
    if request.method == 'GET':
        cursor = g.db.execute('SELECT t.created, t.id, t.content, u.username ' \
                              'FROM tweet t INNER JOIN user u ' \
                              'ON t.user_id = u.id WHERE t.id = :id', param)
        data = cursor.fetchone()
        
        if data:
            result = dict(date=data[0].replace(' ', 'T'), id=data[1], 
                                   content=data[2], uri='/tweet/{}'.format(data[1]),
                                   profile='/profile/{}'.format(data[3]))
            
            return (jsonify(result), 200)
        else:
            return 'Tweet Id not found', 404
    else:
        cursor = g.db.execute('SELECT * FROM tweet WHERE id = :id', param)
        tweet = cursor.fetchone()
        if tweet == None:
            return 'tweet id does not exists', 404
        
        request_data = request.get_json()
        cursor = g.db.execute('SELECT user_id FROM auth WHERE access_token = :access_token', 
                                { 'access_token' : request_data['access_token']})
        auth = cursor.fetchone()
        param['user_id'] = auth[0]
        
        cursor = g.db.execute('SELECT t.created, t.id, t.content, u.username ' \
                              'FROM tweet t INNER JOIN user u ' \
                              'ON t.user_id = u.id ' \
                              'WHERE t.id = :id ' \
                              'AND t.user_id = :user_id', param)
        data = cursor.fetchone()
        if data:
            g.db.execute('DELETE FROM tweet WHERE id = :id', param)
            g.db.commit()
            return 'Tweet deleted', 204
        else:
            return 'Unable to delete tweet that does not belong to you', 401

@app.route('/tweet', methods=['POST'])
@json_only
@auth_only
def post_tweet():
    data = request.get_json()
    
    cursor = g.db.execute('SELECT user_id FROM auth WHERE access_token = :access_token', 
                            { 'access_token' : data['access_token'] })
    auth = cursor.fetchone()
        
    params = {
        'user_id' : auth[0],
        'content' : data['content']
    }
    g.db.execute('INSERT INTO tweet (user_id, content) VALUES ( '\
                  ':user_id, :content);', params)
    g.db.commit()
    return 'Inserted tweet', 201

@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
