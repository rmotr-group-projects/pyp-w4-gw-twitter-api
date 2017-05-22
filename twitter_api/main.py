import sqlite3
import json
import random
import string
from twitter_api.utils import md5, json_only, auth_only

from flask import abort
from flask import Flask
from flask import request
from flask import g

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])

def random_string():
    return "".join(random.choice(string.printable) for _ in range(20))

# implement your views here
@app.route('/login', methods=['POST'])
@json_only
def login(data):
    # actually check that the user is in
    user_name = data['username']
    cursor = g.db.cursor() # https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.execute
    cursor.execute('SELECT id, password FROM user WHERE username=?', (user_name,))
    result = cursor.fetchone()
    
    
    if result is None:

        return abort(404)
    else:
        try:
            password_hash = md5(data['password']).hexdigest() 
        except KeyError:
            return abort(400)
        if result[1] != password_hash:
            return abort(401)
        else:
            # generate the token, return the token, add to auth db
            access_token = random_string()
            user_id = result[0]
            g.db.execute('INSERT INTO auth (user_id, access_token) VALUES (?, ?)', [user_id, access_token])
            g.db.commit()
    return json.dumps({'access_token': access_token}), 201

@app.route('/logout', methods=['POST'])
@json_only
def logout(data):
    try:
        access_token = data['access_token']
        g.db.execute('DELETE FROM auth WHERE access_token=?', [access_token])
        g.db.commit()
        return '', 204
    except KeyError:
        return abort(401)

def parse_tweet(tweet_row, tweet_field='text'):
    """
    id INTEGER PRIMARY KEY autoincrement,
    user_id INTEGER,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user(id)
    """
    tweet_id, user_id, created, content = tweet_row
    uri_string = '/tweet/{}'.format(tweet_id)
    
    # created == "YYYY-MM-DD TTTTTT"
    # created.split() == ["YYYY-MM-DD", "TTTTTT"]
    # 
    created_string = "T".join(created.split())
    return {
        'date':created_string,
        'id': tweet_id,
        tweet_field: content,
        'uri': uri_string
    }

@app.route('/profile', methods=['POST'])
@json_only
def post_profile(data):
        
    try:
        #validate that data is of a proper form
        access_token = data['access_token'] #checks if data['access_token'] exists by assignment
        if len(data) != 4:#check that all required fields are present
            return abort(400)
            
        #verify that access_token is registered to db
        cursor = g.db.execute('SELECT id FROM auth WHERE access_token=?', [access_token]) #moves cursor to auth record matching access_token
        account_info = cursor.fetchone()
        if not account_info:#if no matching auth record exists, abort
            return abort(401)
            
   
        
        # UPDATE table_name
        # SET column1 = value1, column2 = value2...., columnN = valueN
        # WHERE [condition];
        g.db.execute('UPDATE user SET first_name=?, last_name=?, birth_date=? WHERE id=?', [data['first_name'], data['last_name'], data['birth_date'], account_info[0]])
        g.db.commit()
        
        return '', 201
    except KeyError:
        return abort(401)


@app.route('/tweet/<tweet_num>', methods=['DELETE'])
@json_only
def delete_tweet(tweet_num, data):
    
    cursor = g.db.execute('SELECT * FROM tweet WHERE id=?', [tweet_num])
    result = cursor.fetchone()
    if result is None:
        return abort(404)
    else:
        user_id = result[1]
        cursor = g.db.execute('SELECT username FROM user WHERE id=?', [user_id])
        user_name = cursor.fetchone()[0]
        # does user_name's access_token match the access_token from the data
        access_token = data['access_token'] #checks if data['access_token'] exists by assignment
        
        #verify that access_token is registered to db
        cursor = g.db.execute('SELECT id FROM auth WHERE access_token=?', [access_token]) #moves cursor to auth record matching access_token
        account_result = cursor.fetchone()
        if account_result is None:
            return abort(401)
        account_info = account_result[0]
        
        if account_info != user_id:
            return abort(401)
        # UPDATE table_name
        # SET column1 = value1, column2 = value2...., columnN = valueN
        # WHERE [condition];
        g.db.execute('DELETE FROM tweet WHERE id=?', [tweet_num])
        g.db.commit()
        return '', 204

@app.route('/tweet/<tweet_num>', methods=['GET'])
def get_tweet(tweet_num):
    cursor = g.db.execute('SELECT * FROM tweet WHERE id=?', [tweet_num])
    result = cursor.fetchone()
    if result is None:
        return abort(404)
    else:
        user_id = result[1]
        cursor = g.db.execute('SELECT username FROM user WHERE id=?', [user_id])
        user_name = cursor.fetchone()[0]
        tweet_dict = parse_tweet(result, tweet_field='content')
        tweet_dict['profile'] = "/profile/{}".format(user_name)
        return json.dumps(tweet_dict), 200, {'Content-Type': 'application/json'}
        
            


@app.route('/tweet', methods=['POST'])
@json_only
def post_tweet(data):
        
    try:
        #validate that data is of a proper form
        access_token = data['access_token'] #checks if data['access_token'] exists by assignment
        if len(data) != 2:#check that all required fields are present
            return abort(400)
            
        #verify that access_token is registered to db
        cursor = g.db.execute('SELECT id FROM auth WHERE access_token=?', [access_token]) #moves cursor to auth record matching access_token
        account_result = cursor.fetchone()
        if account_result is None:
            return abort(401)
        account_info = account_result[0]
            
        # UPDATE table_name
        # SET column1 = value1, column2 = value2...., columnN = valueN
        # WHERE [condition];
        g.db.execute('INSERT INTO tweet (user_id, content) VALUES (?, ?)', [account_info, data['content']])
        g.db.commit()
        
        return '', 201
    except KeyError:
        return abort(401)

@app.route('/profile/<user_name>', methods=['GET'])
def user_page(user_name):
    cursor = g.db.execute('SELECT * FROM user WHERE username=?', [user_name])
    user_data = cursor.fetchone()

    if user_data is None:
        return abort(404)
    cursor = g.db.execute('SELECT * FROM tweet WHERE user_id=?', [user_data[0]])
    tweet_data = [parse_tweet(tweet) for tweet in cursor.fetchall()]

    user_id, username, _, first_name, last_name, birth_date = user_data
    
    
    result_dict = {
            'user_id': user_id,
            'username': user_name,
            'first_name': first_name,
            'last_name': last_name,
            'birth_date': birth_date,
            'tweets': tweet_data,
            'tweet_count': len(tweet_data),
        }
    
    return json.dumps(result_dict), 200,  {'Content-Type':'application/json'}
    
        

@app.errorhandler(404)
def not_found(e):
    '''
    Client was able to communicate with a given server, 
    but the server could not find what was requested.
    '''
    return '', 404


@app.errorhandler(401)
def not_found(e):
    '''
    Unauthorized: Access is denied due to invalid credentials.
    '''
    return '', 401
