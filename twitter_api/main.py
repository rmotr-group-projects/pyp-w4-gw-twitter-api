import sqlite3

from functools import wraps

from flask import Flask
from flask import g, request, abort, make_response, jsonify
import os
import hashlib
import string
import random
import collections

from .utils import *

app = Flask(__name__)

app.config['JSON_SORT_KEYS'] = False


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


@app.route('/login', methods=['POST'])
@valid_json_required
def login():
    if not 'username' in request.get_json():
      return make_response(jsonify({'error': 'No username given. Cannot log in.'}), 400) 
    # First get the username
    username = request.get_json()['username'].strip()
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
    raw_password = request.get_json()['password']
    
    if len(raw_password) == 0:
        return make_response(jsonify({'error': 'Supplied password was blank. Cannot log in.'}), 400) 
        
    encoded_password = raw_password.encode('utf-8')
    hashed_password = hashlib.md5(encoded_password).hexdigest()
    print("hashed_password is {} and results[0][2] is {} ".format(hashed_password, results[0][2]))
    if hashed_password != results[0][2]:
        return make_response(jsonify({'error': 'Password incorrect. Please try again'}), 401)
    else:
        # Successfully authenticated. Now we generate a token to send back,
        # and store it in the 'auth' table
        token_list = random.sample(string.ascii_letters + string.digits, 10)
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
def public_profile(username):
    # Get the requested profile
    sql_string = '''
        SELECT
        id,
        username,
        first_name,
        last_name,
        birth_date
        FROM
        user
        WHERE
        username = '{}';
    '''
    sql_string = sql_string.format(username)
    print("sql_string is {}".format(sql_string))
    
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
    json_dict = collections.OrderedDict([
        ("user_id", results[0][0]),
        ("username", results[0][1]),
        ("first_name", results[0][2]),
        ("last_name", results[0][3]),
        ("birth_date", results[0][4]),
        ("tweet", []),
        ("tweet_count", 0)
       ]) 
    
    # Next, we need to retrieve the lsit of tweets corresponding to this user
    sql_string = '''
        SELECT
        id,
        content,
        created
        FROM
        tweet
        WHERE
        user_id = {};
    '''
    sql_string = sql_string.format(json_dict['user_id'])
    print("sql_string is {}".format(sql_string))
    
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
            tweet = collections.OrderedDict([
                ("id", tweet_id),
                ("text", result[1]),
                ("date", result[2]),
                ("uri", uri_string)
               ]) 
            tweets.append(tweet)
        json_dict['tweet'] = tweets
        json_dict['tweet_count'] = len(results)
    #Now, we convert the dictionary to JSON and return it
    return make_response(jsonify(json_dict), 200) 


@app.route('/profile', methods=['POST'])
@valid_json_required
@valid_token_required
def update_profile():
    # First, we need to check that all required fields have been supplied
    required_fields = ['first_name', 'last_name', 'birth_date']
    for field in required_fields:
        if field not in request.json:
            return make_response(jsonify({'error': 'One or more required fields are missing. Cannot update user profile'}), 400) 
            
    # Next, we need to get the user_id from the supplied access token
    sql_string = '''
        SELECT
        user_id
        FROM
        auth
        WHERE
        access_token = "{}";
    '''
    sql_string = sql_string.format(request.json['access_token'])
    print("sql_string is {}".format(sql_string))
    
    try:
        cursor = g.db.execute(sql_string)
    except:
        return make_response(jsonify({'error': 'Internal server error. Could not update user profile'}), 500) 
    results = cursor.fetchall()
    print("results is {}".format(results))
    
    sql_string = '''
        UPDATE
        user
        SET
        first_name = '{}',
        last_name = '{}',
        birth_date = '{}'
        WHERE
        id = {};
    '''
    sql_string = sql_string.format(
        request.json['first_name'],
        request.json['last_name'],
        request.json['birth_date'],
        results[0][0]
        )
    print("sql_string is {}".format(sql_string))
    try:
        cursor = g.db.execute(sql_string)
        g.db.commit()
    except:
        return make_response(jsonify({'error': 'Internal server error. Could not update user profile'}), 500) 
    print("results is {}".format(results))
    return make_response(jsonify({'Success': 'Profile successfully updated'}), 201) 

@app.route('/tweet/<tweet_id>', methods=['GET'])
def retrieve_tweet(tweet_id):
    try:
        tweet_id = int(tweet_id)
    except ValueError:
        return make_response(jsonify({'error': 'Bad request. Tweets can only be requested by their numeric ID'}), 400) 
        
    sql_string = '''
        SELECT
        content,
        created,
        user_id
        FROM
        tweet
        WHERE
        id = {}
    '''
    sql_string = sql_string.format(tweet_id)
    print("sql_string is {}".format(sql_string))
    
    try:
        cursor = g.db.execute(sql_string)
    except:
        return make_response(jsonify({'error': 'Internal server error. Could not retrieve requested tweet'}), 500) 
        
    results_1 = cursor.fetchall()
    print("results_1 is {}".format(results_1))

    if len(results_1) == 0:
       return make_response(jsonify({'error': 'Could not find specified tweet'}), 404)
    if len(results_1) >1:
       return make_response(jsonify({'error': 'More than one tweet with this id exists! Aborting.'}), 500)
    #If we get here, we have a tweet to return
    #We need the username to return the profile path
    sql_string = '''
        SELECT
        username
        FROM
        user
        WHERE
        id = {}
    '''
    sql_string = sql_string.format(results_1[0][2])
    print("sql_string is {}".format(sql_string))
    
    try:
        cursor = g.db.execute(sql_string)
    except:
        return make_response(jsonify({'error': 'Internal server error. Could not retrieve requested tweet'}), 500) 
        
    results_2 = cursor.fetchall()
    print("results_2 is {}".format(results_2))
    
    
    # Now we begin to construct the JSON data to return
    profile_string = "/profile/{}".format(results_2[0][0])
    uri_string = "/tweet/{}".format(tweet_id)
    json_dict = collections.OrderedDict([
        ("id", tweet_id),
        ("content", results_1[0][0]),
        ("date", results_1[0][1]),
        ("profile", profile_string),
        ("uri", uri_string)
       ]) 

    # Finally, we return the JSON version of the dictionary
    return make_response(jsonify(json_dict), 200)
    
    

@app.route('/tweet', methods=['POST'])
@valid_json_required
@valid_token_required
def create_tweet():
    # First check that the text of the tweet has been supplied
    tweet_text = request.json.get('content','').strip()
    if len(tweet_text) == 0:
        return make_response(jsonify({'error': 'Tweet text not supplied. Cannot create tweet.'}), 400) 
    
    # Now get the user_id associated with the supplied access token
    sql_string = '''
        SELECT
        user_id
        FROM
        auth
        WHERE
        access_token = "{}"
    '''
    sql_string = sql_string.format(request.json['access_token'])
    print("sql_string is {}".format(sql_string))
    
    try:
        cursor = g.db.execute(sql_string)
    except:
        return make_response(jsonify({'error': 'Internal server error. Could not create tweet.'}), 500) 
        
    results = cursor.fetchall()
    print("results is {}".format(results))
    if len(results) == 0:
        return make_response(jsonify({'error': 'Internal server error. Could not create tweet. Access token not found.'}), 500) 
    if len(results) > 1:
        return make_response(jsonify({'error': 'Internal server error. Could not create tweet. More than one instance of the same access token found.'}), 500) 
        
    sql_string = '''
        INSERT
        INTO
        tweet
        (
        user_id,
        content
        )
        VALUES
        (
        {},
        "{}"
        )
        ;
    '''
    sql_string = sql_string.format(
        results[0][0],
        tweet_text
        )
    print("sql_string is {}".format(sql_string))
    try:
        cursor = g.db.execute(sql_string)
        g.db.commit()
    except:
        return make_response(jsonify({'error': 'Internal server error. Could not create tweet'}), 500) 
    results = cursor.fetchall()
    print("results is {}".format(results))
    
    return make_response(jsonify({'Success': 'Tweet created'}), 201) 
    
@app.route('/tweet/<tweet_id>', methods=['DELETE'])
@valid_json_required
@valid_token_required
def delete_tweet(tweet_id):
    #First check if the tweet id is a valid number
    try:
        tweet_id = int(tweet_id)
    except ValueError:
        return make_response(jsonify({'error': 'Bad request. Tweets can only be requested by their numeric ID'}), 400) 
        
    #Now see if this tweet actually exists and who it belongs to
    sql_string = '''
        SELECT
        user_id
        FROM
        tweet
        WHERE
        id = {}
    '''
    sql_string = sql_string.format(tweet_id)
    print("sql_string is {}".format(sql_string))
    
    try:
        cursor = g.db.execute(sql_string)
    except:
        return make_response(jsonify({'error': 'Internal server error. Could not delete tweet.'}), 500)
        
    results = cursor.fetchall()
    print("results is {}".format(results))
    
    if len(results) == 0:
        return make_response(jsonify({'error': 'Tweet with id {} not found. Cannot delete'.format(tweet_id)}), 404)
    if len(results) > 1:
        return make_response(jsonify({'error': 'Internal server error. Could not delete tweet. More than one instance of the same tweet found.'}), 500) 
    tweet_owner = results[0][0]
        
    # Now get the user_id associated with the supplied access token
    sql_string = '''
        SELECT
        user_id
        FROM
        auth
        WHERE
        access_token = "{}"
    '''
    sql_string = sql_string.format(request.json['access_token'])
    print("sql_string is {}".format(sql_string))
    
    try:
        cursor = g.db.execute(sql_string)
    except:
        return make_response(jsonify({'error': 'Internal server error. Could not create tweet.'}), 500) 
        
    results = cursor.fetchall()
    print("results is {}".format(results))
    if len(results) == 0:
        return make_response(jsonify({'error': 'Internal server error. Could not delete tweet. Access token not found.'}), 500) 
    if len(results) > 1:
        return make_response(jsonify({'error': 'Internal server error. Could not delete tweet. More than one instance of the same access token found.'}), 500) 
    authorised_user = results[0][0] 
    # Check that the owner of the twee to be deleted and the authorised user are the same
    if authorised_user != tweet_owner:
        return make_response(jsonify({'error': 'You are not the owner of this tweet, so you cannot delete it.'}), 401) 
        
    # Now that we are sure that the specified tweet exists, and that the user is the tweet owner, we can delete it.
    sql_string = '''
        DELETE
        FROM
        tweet
        WHERE
        id = {}
        ;
    '''
    sql_string = sql_string.format(tweet_id)
    print("sql_string is {}".format(sql_string))
    
    try:
        g.db.execute(sql_string)
        g.db.commit()
    except:
        return make_response(jsonify({'error': 'Internal server error. Could not delete tweet.'}), 500) 
        
    return make_response(jsonify({'success': 'Tweet with id {} successfully deleted'.format(tweet_id)}), 204) 
    
