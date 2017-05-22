import sqlite3
import json
import random
import string
from twitter_api.utils import md5, json_only, auth_and_json_only

from flask import abort
from flask import Flask
from flask import request
from flask import g

app = Flask(__name__)


def connect_db(db_name):
    '''
    Helper function that connects to a sqlite3 db
    '''
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    '''
    The API must connect to one specific database before any network requests are processed
    '''
    g.db = connect_db(app.config['DATABASE'])

def random_string():
    '''
        This helper functions always generates a random string of length 20 for the purposes of assigning access_token
        !NOT IMPLEMENTED!
    '''
    return "".join(random.choice(string.printable) for _ in range(20))


@app.route('/login', methods=['POST'])
@json_only
def login(data):
    '''
    Usage: POST request (user submits credentials) while URL ends with '/login'
    
    -data is json pulled from the request object (data = request.get_json()). It is automatically passed
        into this function by way of the json_only decorator.
        
    This function will log the user into the website by generating an auth record if the 
    provided username and password match the record in the db.
    '''
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
    '''
    Usage: POST request (user clicks logout button)
    
    -data is json pulled from the request object (data = request.get_json()). It is automatically passed
        into this function by way of the json_only decorator.
        
    This function will log the user out of the currently active account by removing the user's access_token db complement.
    '''
    try:
        access_token = data['access_token']
        g.db.execute('DELETE FROM auth WHERE access_token=?', [access_token])
        g.db.commit()
        return '', 204
    except KeyError:
        return abort(401)


def parse_tweet(tweet_row, tweet_field='text'):
    '''
        Helper function that fixes a formatting issue with the datetime value in a provided tweet_row
        and maps the values of the tweet_row to a dict with properly named keys.
        
        Returns: formatted tweet dict
        
        NOTE: test_profile_resource presents a unique edge case. We have decided to the use the param 'tweet_field'
            to handle the exception with the default val provided.
            
            text_field == 'text' when tweet content (e.g. text_field) is called 'text' in the profile tests.
            
            For the test_tweet_resource checks and all tweet functions in this program the content of the tweet
            must be assigned to 'content', such that 'parse_tweet(tweet_row, tweet_field='content')
    '''
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
@auth_and_json_only
def post_profile(data, authorized_user_id):
    '''
    Usage: POST request (user clicks submit button on their profile page)
    
    -data is json pulled from the request object (data = request.get_json()). It is automatically passed
        into this function by way of the auth_and_json_only decorator.
        --first_name (str)
        --last_name (str)
        --birth_date (datetime)
        --access_token (str)
        
    -authorized_user_id is the current user's id which is
        derived from the access_token during auth_and_json_only decorator execution
        
    While logged in to an authenticated account, this function updates the user's personal profile information.
    '''
    try:
            
        if len(data) != 4:
            return abort(400)
        
        # UPDATE table_name
        # SET column1 = value1, column2 = value2...., columnN = valueN
        # WHERE [condition];
        g.db.execute('UPDATE user SET first_name=?, last_name=?, birth_date=? WHERE id=?', [data['first_name'], data['last_name'], data['birth_date'], authorized_user_id])
        g.db.commit()
        
        return '', 201
    except KeyError:
        return abort(401)


@app.route('/tweet/<tweet_num>', methods=['DELETE'])
@auth_and_json_only
def delete_tweet(tweet_num, data, authorized_user_id):
    '''
    Usage: DELETE request (user clicks delete button on a tweet they posted)
    
    -data is json pulled from the request object (data = request.get_json()). It is automatically passed
        into this function by way of the auth_and_json_only decorator.
        --access_token (str)
        
    -authorized_user_id is the current user's id which is
        derived from the access_token during auth_and_json_only decorator execution
        
    While logged in to an authenticated account, this function deletes the tweet selected by the user.
    '''
    cursor = g.db.execute('SELECT * FROM tweet WHERE id=?', [tweet_num])
    result = cursor.fetchone()
    if result is None:
        return abort(404)
    else:
        user_id = result[1]
        
        if authorized_user_id != user_id:
            return abort(401)
        # UPDATE table_name
        # SET column1 = value1, column2 = value2...., columnN = valueN
        # WHERE [condition];
        g.db.execute('DELETE FROM tweet WHERE id=?', [tweet_num])
        g.db.commit()
        return '', 204

@app.route('/tweet/<tweet_num>', methods=['GET'])
def get_tweet(tweet_num):
    '''
    Usage: GET request (tweet sepcified in URL)
        
    This returns the tweet record of a given tweet 
    If no such tweet exists in the db a 404 is thrown.
    '''
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
@auth_and_json_only
def post_tweet(data, authorized_user_id):
    '''
    Usage: POST request (user clicks submit button on their tweet feed)
    
    -data is json pulled from the request object (data = request.get_json()). It is automatically passed
        into this function by way of the auth_and_json_only decorator.
        --content (str)
        --access_token (str)
        
    -authorized_user_id is the current user's id which is
        derived from the access_token during auth_and_json_only decorator execution
        
    While logged in to an authenticated account, this function updates the user's personal profile information.
    '''
    try:
        
            
        # UPDATE table_name
        # SET column1 = value1, column2 = value2...., columnN = valueN
        # WHERE [condition];
        g.db.execute('INSERT INTO tweet (user_id, content) VALUES (?, ?)', [authorized_user_id, data['content']])
        g.db.commit()
        
        return '', 201
    except KeyError:
        return abort(401)

@app.route('/profile/<user_name>', methods=['GET'])
def user_page(user_name):
    '''
    Usage: GET request (username sepcified in URL)
        
    This function serves up the tweet feed of a given user_name
    If no user_name exists in the db a 404 is thrown.
    '''
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