import sqlite3

from functools import wraps

from flask import Flask
from flask import g, request, abort, make_response, jsonify
import os
import hashlib
import string
import random

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])

def valid_json_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.json: 
            return make_response(jsonify({'error': 'Request was not valid JSON, or was empty. Unauthorised'}), 401)
        return f(*args, **kwargs)
    return decorated_function
    
    
def valid_token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token'.encode('utf-8') not in request.json:
           return make_response(jsonify({'error': 'No access_token was supplied. Unauthorised.'}), 401)
        # Now retrieve a list of all authorised users
        sql_string = '''
            SELECT
            access_token
            FROM
            auth;
        '''
        cursor = g.db.execute(sql_string)
        results = cursor.fetchall()
        print("results is ", results)
        if len(results) == 0:
            return make_response(jsonify({'error': 'Access token is invalid or has expired. Please log in again'}), 401)
        authorised = False;
        for result in results:
            if result[0] == request.json['access_token'].encode('utf-8'):
                authorised = True;
                print("result[0] is ", result[0])
                # Access token is present in 'auth' table. Proceed with function
        # Supplied access token not found in 'auth' table.
        if authorised:
            print("Authorised, so about to return the original function")
            return f(*args, **kwargs)
        else:
            return make_response(jsonify({'error': 'Access token is invalid or has expired. Please log in again'}), 401)
    return decorated_function

@app.route('/login', methods=['POST'])
@valid_json_required
def login():
    if not 'username'.encode('utf-8') in request.json:
      abort(400)
    # First get the username
    username = request.json['username'].strip()
    if len(username) == 0:
        return make_response(jsonify({'error': 'Supplied username was blank. Cannot log in.'}), 400) 
    sql_string = '''
        SELECT
        id,
        username,
        password
        FROM
        user
        WHERE
        username = '{}'
    '''
    sql_string = sql_string.format(username)
    cursor = g.db.execute(sql_string)
    results = cursor.fetchall()
    if len(results) == 0:
        return make_response(jsonify({'error': 'Supplied username was not found in database. Please try again'}), 404)
    if len(results) != 1:
        return make_response(jsonify({'error': 'There exists more than one of the same username in the database. Aborting!'}), 500)
    # Check to see if a password is supplied
    if 'password' not in request.json:
        return make_response(jsonify({'error': 'No password was supplied. Login failed.'}), 400)
    # Check to see if the password matches
    raw_password = request.json['password'].strip()
    
    if len(raw_password) == 0:
        return make_response(jsonify({'error': 'Supplied password was blank. Cannot log in.'}), 400) 
        
    hashed_password = hashlib.md5(raw_password.encode(request.charset)).hexdigest()
    print("hashed_password is {} and results[0][2] is {} ".format(hashed_password, results[0][2]))
    if hashed_password != results[0][2]:
        return make_response(jsonify({'error': 'Password incorrect. Please try again'}), 401)
    else:
        # Successfully authenticated. Now we generate a token to send back,
        # and store it in the 'auth' table
        token_list = random.sample(string.letters + string.digits, 10)
        token = ''
        for x in token_list:
            token += x
        
        sql_string = '''
            INSERT
            INTO
            'auth'
            (
            'user_id',
            'access_token'
            )
            VALUES
            (
            '{}',
            '{}'
            );
        '''
        sql_string = sql_string.format(results[0][0], token)
        print("sql_string is {}".format(sql_string))
        
        try:
            g.db.execute(sql_string)
            g.db.commit()
            json_response = {
                'access_token': token
            }
            print("finished adding to the database and about to return the json response")
            return make_response(jsonify(json_response), 201)
        except:
            return make_response(jsonify({'error': 'Error saving token to the database. Login failed.'}), 500) 

@app.route('/logout', methods=['POST'])
@valid_json_required
@valid_token_required
def logout():
    print("entering logout()")
    sql_string = '''
        DELETE
        FROM
        auth
        WHERE
        access_token = '{}';
    '''
    sql_string = sql_string.format(request.json['access_token'])
    try:
        # Execute the SQL commant
        print("about to execute the following sql_string:", sql_string)
        g.db.execute(sql_string)
        g.db.commit()
        print("commit was succesful, about to return a 204 status")
        return make_response(jsonify({'success': 'Logged out'}), 204)
    except:
       return make_response(jsonify({'error': 'Internal server error. Logout failed.'}), 500)

@app.route('/profile/<username>', methods=['GET'])
@valid_json_required
def profile(username):
    # Get the requested profile
    sql_string = '''
        SELECT
        id,
        username,
        first_name,
        last_name,
        birth_date
        WHERE
        username = '{}';
    '''
    sql_string = sql_string.format(username)
    
    try:
        cursor = g.db.execute(sql_string)
    except:
       return make_response(jsonify({'error': 'Internal server error. Could not retrieve user profile'}), 500)
    
    results = cursor.fetchall()
    if len(results) == 0:
       return make_response(jsonify({'error': 'Could not find profile of specified user'}), 404)
    if len(results) >1:
       return make_response(jsonify({'error': 'More than one user with this username exists! Aborting.'}), 500)
    
    # Now we begin to construct the JSON data to return
    json_dict = {
        "user_id": results[0][0],
        "username": results[0][1],
        "first_name": results[0][2],
        "last_name": results[0][3],
        "birth_date": results[0][4],
        "tweets": []
        }
    
    # Next, we need to retrieve the lsit of tweets corresponding to this user
    sql_string = '''
        SELECT
        id,
        content,
        created
        FROM
        tweets
        WHERE
        user_id = {}
    '''
    sql_string = sql_string.format(json_dict['user_id'])
    try:
        cursor = g.db.execute(sql_string)
    except:
       return make_response(jsonify({'error': 'Internal server error. Could not retrieve user profile'}), 500)
    
    results = cursor.fetchall()
    if len(results) > 0: 
        # There is at least one tweet associated with this user, so we need
        # to build up a list of tweets to append to the profile data
        tweets = []
        for result in results:
            tweet_id = result[0]
            uri_string = "/tweet/{}".format(tweet_id)
            tweet = {
                "id": tweet_id,
                "text": result[1],
                "date": result[2],
                "uri": uri_string 
                }
            tweets.append(tweet)
        json_dict['tweets'] = tweets
    #Now, we convert the dictionary to JSON and return it
    return make_response(jsonify(json_dict), 200) 


# TODO: Not sure whether I will require this...
# @app.errorhandler(404)
# def not_found(e):
#     return '', 404


# @app.errorhandler(400)
# def bad_request(e):
#     return '', 400
