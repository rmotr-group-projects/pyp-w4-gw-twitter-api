import json
import sqlite3

from twitter_api.utils import hash_to_md5
from twitter_api.settings import SALT
from flask import Flask, g, request, Response


app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])



@app.route('/login', methods=['POST'])
def login():
    # Get user credentials from request
    user_data = json.loads(request.data.decode('utf-8'))
    
    # Validate required params
    try:
        username = user_data['username']
        password = user_data['password']
    except KeyError:
        return Response(status=400)
    
    # Query user table to get user data
    query = """
        SELECT id, username, password 
        FROM user 
        WHERE username=:username;
    """
    cursor = g.db.execute(query, {'username': username})
    user_in_db = cursor.fetchone()
    
    # Validate user exists and passwords match
    if not user_in_db:
        return Response(status=404)
    
    if user_in_db[2] != hash_to_md5(password):
        return Response(status=401)

    if user_in_db[2] == hash_to_md5(password):
        # Create access_token and query auth table to save it
        access_token = hash_to_md5('{}{}{}'.format(SALT, username, password))
        query = """
            INSERT INTO auth (user_id, access_token) 
            VALUES (:user_id, :access_token);
        """
        g.db.execute(
            query, {'user_id': user_in_db[0], 'access_token': access_token})
        g.db.commit()
        
        # Build object to send in response
        json_response = json.dumps({'access_token': access_token})
        return Response(json_response, status=201)
    
     
@app.route('/logout', methods=['POST'])
def logout():
    # Get access_token from request.data
    try:
        access_token = json.loads(request.data.decode('utf-8'))['access_token']
    except KeyError:
        return Response(status=401)
    
    # Check if given access_token is valid
    query = """
        SELECT user_id 
        FROM auth 
        WHERE access_token=:access_token;
    """
    cursor = g.db.execute(query, {'access_token': access_token})
    user_id = cursor.fetchone()
    
    if not user_id:
        return Response(status=404)
    
    # Query auth table to delete access_token from user
    query = """
        DELETE FROM auth 
        WHERE access_token=:access_token;
    """
    g.db.execute(query, {'access_token': access_token})
    g.db.commit()
    
    return Response(status=204)
    

@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    # Query user table to get user data
    query = """
        SELECT id, first_name, last_name, birth_date 
        FROM user WHERE username=:username;
    """
    cursor = g.db.execute(query, {'username': username})
    user = cursor.fetchone()

    if not user:
        return Response(status=404)
    
    # Query tweet table to get all tweets from user
    user_id = user[0]
    query = """
        SELECT id, content, created FROM tweet WHERE user_id=:user_id;
    """
    cursor = g.db.execute(query, {'user_id': user_id})
    tweets = cursor.fetchall()
    tweets_list = [
        {
            'id': tweet[0], 
            'text': tweet[1], 
            'date': 'T'.join(tweet[2].split()),
            'uri': '/tweet/{}'.format(tweet[0])
        } for tweet in tweets
    ]
    
    # Build object to send in response
    response_obj = {}
    response_obj['user_id'] = user_id
    response_obj['username'] = username
    response_obj['first_name'] = user[1]
    response_obj['last_name'] = user[2]
    response_obj['birth_date'] = user[3]
    response_obj['tweet'] = tweets_list
    response_obj['tweet_count'] = len(tweets_list)
    
    return Response(
        json.dumps(response_obj), status=200, mimetype='application/json')
        

@app.route('/profile', methods=['POST'])
def post_profile():
    # Get access_token from request.data
    try:
        access_token = json.loads(request.data.decode('utf-8'))['access_token']
    except KeyError:
        return Response(status=401)
        
    try:
        first_name = json.loads(request.data.decode('utf-8'))['first_name']
        last_name = json.loads(request.data.decode('utf-8'))['last_name']
        birth_date = json.loads(request.data.decode('utf-8'))['birth_date']
    except KeyError:
        return Response(status=400)
        
    # Query auth table with access_token and get user_id
    query = """
        SELECT user_id FROM auth WHERE access_token=:access_token;
    """
    cursor = g.db.execute(query, {'access_token': access_token})
    user = cursor.fetchone()
    if not user:
        return Response(status=401)

    # Update user in user table
    query = """
        UPDATE user SET first_name=:first_name, last_name=:last_name,
        birth_date=:birth_date WHERE id=:id;
    """
    g.db.execute(
        query, 
        {'first_name': first_name, 'last_name': last_name,
         'birth_date': birth_date, 'id': user[0]}
    )
    g.db.commit()
    
    # Build object to send in response
    response_obj = {}
    response_obj['first_name'] = first_name
    response_obj['last_name'] = last_name
    response_obj['birth_date'] = birth_date
    response_obj['access_token'] = access_token
    
    return Response(
        json.dumps(response_obj), status=201, mimetype='application/json')
    

@app.route('/tweet/<tweet_id>', methods=['GET'])
def get_tweet(tweet_id):
    # Get tweet data from tweet table
    query = """
        SELECT created, content, username 
        FROM tweet 
        INNER JOIN user ON tweet.user_id=user.id 
        WHERE tweet.id=:tweet_id
    """
    cursor = g.db.execute(query, {'tweet_id': tweet_id})
    tweet = cursor.fetchone()

    if not tweet:
        return Response(status=404)

    # Build response object
    response_obj = {}
    response_obj['id'] = int(tweet_id)
    response_obj['content'] = tweet[1]
    response_obj['date'] = 'T'.join(tweet[0].split())
    response_obj['profile'] = '/profile/{}'.format(tweet[2])
    response_obj['uri'] = '/tweet/{}'.format(tweet_id)
    
    return Response(
        json.dumps(response_obj), status=200, mimetype='application/json')

@app.route('/tweet', methods=['POST'])
def post_tweet():
    # Check that given data is json
    if request.content_type != 'application/json':
        return Response(status=400)

    # Check that access_token and content from the tweet were given
    try:
        access_token = json.loads(request.data.decode('utf-8'))['access_token']
    except KeyError:
        return Response(status=401)
        
    try:
        content = json.loads(request.data.decode('utf-8'))['content']
    except KeyError:
        return Response(status=400)
        
    # Query auth table with access_token and get user_id
    query = """
        SELECT user_id 
        FROM auth 
        WHERE access_token=:access_token;
    """
    cursor = g.db.execute(query, {'access_token': access_token})
    user_id = cursor.fetchone()

    if not user_id:
        return Response(status=401)
    user_id = user_id[0]        # Get user_id from user_id tuple

    # Insert tweet data into tweet table
    query = """
        INSERT INTO tweet (user_id, content) VALUES (:user_id, :content)
    """
    g.db.execute(query, {'user_id': user_id, 'content': content})
    g.db.commit()
    
    return Response(status=201)
    
    
@app.route('/tweet/<tweet_id>', methods=['DELETE'])
def delete_tweet(tweet_id):
    # Check that access_token and content from the tweet were given
    try:
        access_token = json.loads(request.data.decode('utf-8'))['access_token']
    except KeyError:
        return Response(status=401)  
        
    # Get user_id from auth table with given access_token
    query = """
        SELECT user_id 
        FROM auth 
        WHERE access_token=:access_token;
    """
    cursor = g.db.execute(query, {'access_token': access_token})
    user_id = cursor.fetchone()
    
    if not user_id:
        return Response(status=401)
    
    # Get tweet from tweet table with given tweet_id
    query = """
        SELECT *
        FROM tweet 
        WHERE id=:tweet_id;
    """
    cursor = g.db.execute(query, {'tweet_id': tweet_id})
    tweet = cursor.fetchone()
    
    if not tweet:
        return Response(status=404)
        
    # Check the tweet corresponds to given user
    if user_id[0] != tweet[1]:
        return Response(status=401)
        
    # Query tweet table to delete row of tweet_id
    query = """
        DELETE FROM tweet 
        WHERE id=:tweet_id;
    """
    g.db.execute(query, {'tweet_id': tweet_id})
    g.db.commit()        
    
    return Response(status=204)


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
