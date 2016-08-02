import sqlite3, os, binascii, json

from flask import Flask
from flask import g, request, jsonify, Response
from hashlib import md5
from utils import JSON_MIME_TYPE


app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])
    
    
"""
#edit to verify access token
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
"""


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401


@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        if 'password' not in request.get_json().keys():
            return Response(status=400)

        #Creates query that checks if there is a username/password combination
        #within the SQLite3 DB
        username = request.get_json()['username']
        password = request.get_json()['password']
        
        query = "SELECT * FROM user WHERE username=:username"
        value =  g.db.execute(query, {'username': username})
        if value.fetchone() is None:
            return Response(status=404)
        
        query = "SELECT * FROM user WHERE username=:username AND password=:password"
        val = g.db.execute(query, {
            'username' : username,
            'password' : md5(password).hexdigest()})
            
        row = val.fetchone()
        
        #If there's a result, then correct JSON data and upload
        if row:
            user_id = row[0] #User ID of row matched
            access_token = binascii.b2a_hex(os.urandom(15))
            g.db.execute('INSERT INTO auth(user_id, access_token) VALUES(:user_id, :access_token)',\
                        {"user_id":user_id, "access_token":access_token})
            g.db.commit()
            return json.dumps({'access_token': access_token}), 201, {'Content-Type': JSON_MIME_TYPE}
            
        else:
            return Response(status=401)
        
 
@app.route('/logout', methods = ['POST'])
#@login_required
def logout():
    if 'access_token' in request.get_json().keys():
        g.db.execute('DELETE FROM auth WHERE access_token=:access_token', \
                    {'access_token' : request.get_json()['access_token']})
        g.db.commit()
        return json.dumps({'access_token' : ''}), 204, {'Content-Type': JSON_MIME_TYPE} 
   
    else:
        return Response(status=401)
    

@app.route('/profile/<username>', methods = ['GET'])
#@login_required
def profile(username):
    if request.method == 'GET':
        value = g.db.execute("SELECT id, username, first_name, last_name, birth_date FROM user WHERE username=:username", 
                            {'username': username})
        user = value.fetchone()
        if user is None:
            return Response(status=404)
        user_id = user[0]
        
        tweets = g.db.execute("SELECT  id, content FROM tweet WHERE user_id=:user_id", {'user_id':user[0]})
        tweetCount = 0
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
            
        jsonData = {
            'user_id': user[0],
            'username': user[1],
            'first_name': user[2],
            'last_name': user[3],
            'birth_date': user[4],
            'tweet': tweets_list,
            'tweet_count': len(tweets_list)
        }
        return json.dumps(jsonData), 200, {'Content-Type': JSON_MIME_TYPE}  
            
    
                  
@app.route('/profile', methods = ['POST'])  
def post_prof():
    if request.method == 'POST':         
        if request.content_type != 'application/json':
            return Response(status = 400)
            
        if 'access_token' not in request.get_json().keys():
            return Response(status = 401)
        
        if 'first_name' not in request.get_json().keys() or 'last_name' not in request.get_json().keys():
            return Response(status = 400)
        
        access_token = request.get_json()['access_token']
        first_name = request.get_json()['first_name']
        last_name = request.get_json()['last_name']
        birth_date = request.get_json()['birth_date']
        
        value = g.db.execute('SELECT user_id FROM auth WHERE access_token=:access_token', {'access_token': access_token})
        authRow = value.fetchone()
        if authRow:
            user_id = authRow[0]
            query = """ SELECT first_name, last_name, birth_date FROM user WHERE id=:user_id """
            userCredentialsTotal = g.db.execute(query, {'user_id':user_id})
            userCredentials = userCredentialsTotal.fetchone()
            
            g.db.execute('UPDATE user SET first_name=:first_name, last_name=:last_name, birth_date=:birth_date WHERE id=:user_id;', 
                         {'first_name' : first_name, 'last_name': last_name, 'birth_date': birth_date, 'user_id': user_id})
            g.db.commit()
            
            return Response(status=201)
        else:
            return Response(status=401)

@app.route('/tweet/<tweet_id>', methods = ['GET', 'DELETE'])
def getTweet(tweet_id):
     if request.method == 'DELETE':
        access_token = request.get_json()['access_token']
        
        tweetIdConfirmation = g.db.execute("SELECT * FROM tweet WHERE tweet.id=:tweet_id", {'tweet_id' : tweet_id})
        if tweetIdConfirmation.fetchone() is None:
            return Response(status=404)
            
        result = g.db.execute("SELECT * FROM auth, tweet WHERE tweet.id=:tweet_id AND auth.user_id = tweet.user_id AND auth.access_token=:access_token", 
                             {'tweet_id' : tweet_id, 'access_token' : access_token})
        if result.fetchone() is None:
            return Response(status=401)
        
        g.db.execute("DELETE FROM tweet WHERE tweet.id=:tweet_id", {'tweet_id' : tweet_id})
        g.db.commit()
        return Response(status=204)
     
     if request.method == 'GET':
        tweetIdConfirmation = g.db.execute("SELECT * FROM tweet WHERE tweet.id=:tweet_id", {'tweet_id' : tweet_id})
        if tweetIdConfirmation.fetchone() is None:
            return Response(status=404)
        
                
        tweetInfoAll = g.db.execute("SELECT tweet.id, content, created, username FROM tweet, user WHERE user_id = user.id AND tweet.id=:tweet_id", 
                                    {'tweet_id' : tweet_id})
        tweetInfo = tweetInfoAll.fetchone()
        jsonData = {
            'id':tweetInfo[0],
            'content':tweetInfo[1],
            'date': 'T'.join(tweetInfo[2].split()),
            'profile': '/profile/{}'.format(tweetInfo[3]),
            'url': '/tweet/{}'.format(tweet_id)
        }
        return json.dumps(jsonData), 200, {'Content-Type': JSON_MIME_TYPE}
    
        
@app.route('/tweet', methods = ['POST'])
def postTweet():
    if request.content_type != 'application/json':
        return Response(status = 400)
    if 'access_token' not in request.get_json().keys():
        return Response(status = 401)
            
    access_token = request.get_json()['access_token']
    content = request.get_json()['content']
    
    value = g.db.execute('SELECT user_id FROM auth WHERE access_token=:access_token', {'access_token': access_token})
    authRow = value.fetchone()
    if authRow:
        user_id = authRow[0]
        g.db.execute("INSERT INTO tweet(content, user_id) VALUES(:content,:user_id)", {'content' : content, 'user_id' : user_id})
        g.db.commit()
        
        return Response(status = 201)
    else:
        return Response(status = 401)