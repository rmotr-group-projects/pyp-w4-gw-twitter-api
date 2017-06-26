import sqlite3
import json 

from flask import Flask
from flask import g, request, make_response, abort
from .utils import md5, JSON_MIME_TYPE, auth_only, json_only

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here
@app.route('/login', methods=['POST'])
def user_login():
    username = request.json.get('username')
    password = request.json.get('password')
    if password is None: 
        return '',400 #no password given
    pwhash = md5(password).hexdigest()
    
    query = "select id from user where username = :username and password = :password;"
    cursor = g.db.execute(query, {'username': username, 'password': pwhash})
    db_user = cursor.fetchone()
    if db_user is not None:
        db_user_id = db_user[0]
        access_token = md5("randomtext").hexdigest() #<- Create Access Token
        response_dict = {"access_token": access_token}
        
        query = "INSERT INTO auth ('user_id', 'access_token') VALUES (:db_user_id, :access_token);"
        g.db.execute(query,{'db_user_id': db_user_id, 'access_token': access_token})
        g.db.commit()
        
        return make_response( json.dumps(response_dict), 201)
    else:
        query = "select id from user where username = :username;"
        cursor = g.db.execute(query, {'username': username})
        db_user = cursor.fetchone()
        if db_user:
            return '', 401 #wrong password
        else:
            return '', 404 #user given but doesn't exist
            
            

@app.route('/profile', methods = ['POST'])
@json_only
@auth_only
def profile_create():
    profile_dict = request.get_json()
    access_token = profile_dict.get('access_token')
    first_name = profile_dict.get('first_name', None)
    last_name = profile_dict.get('last_name', None)
    birth_date = profile_dict.get('birth_date', None)

    if not all([first_name, last_name, birth_date]):
        return '', 400

    query = "SELECT user_id FROM auth WHERE access_token = :access_token;"
    cursor = g.db.execute( query, {'access_token':access_token})
    db_result = cursor.fetchone()
    if not db_result:
        return abort(401)
    user_id = db_result[0]
    
    query = "UPDATE user SET first_name = :first_name, last_name = :last_name, birth_date = :birth_date WHERE id = :user_id;"
    query_dict = {
        'user_id' : user_id, 
        'first_name' : first_name, 
        'last_name' : last_name, 
        'birth_date' : birth_date
    }
    print(query)
    cursor = g.db.execute( query, query_dict )
    g.db.commit()
    return '', 201


@app.route('/profile/<username>', methods = ['GET'])
def profile_get(username):
    
    query1 = """
        SELECT id, first_name, last_name, birth_date FROM user 
        WHERE username=:username;
    """
    cursor = g.db.execute(query1, {'username' : username})
    db_user = cursor.fetchone()
    if db_user is None:
        return '', 404
    
    
    # getting all the tweets for the user
    query2 = """
        SELECT b.id, b.content, b.created
        FROM tweet b INNER JOIN user a on a.id = b.user_id
        WHERE a.username = :username
        """
    cursor = g.db.execute( query2, {'username': username})
    db_tweets = cursor.fetchall()
    list_tweets = []
    for row in db_tweets:
        list_tweets.append ({
                    'id': row[0],
                    'text': row[1],
                    'date': row[2].replace(' ','T'),
                    'uri': '/tweet/{}'.format(row[0])
                })
    
    result_dict = {
        'user_id': db_user[0],
        'username' : username,
        'first_name' : db_user[1],
        'last_name' : db_user[2],
        'birth_date' : db_user[3],
        'tweets' : list_tweets,
        'tweet_count': len(list_tweets)
    }
    return make_response(json.dumps(result_dict), 200, {'Content-Type':JSON_MIME_TYPE})
        
            
@app.route('/logout', methods = ['POST'])
def user_logout():
    request_dict = request.get_json()
    access_token = request_dict.get('access_token', None)
    if not access_token:
        return '', 401  #access token missing
    
    query = "DELETE FROM auth where access_token = :access_token;"
    #query = "DELETE FROM auth where user_id=1;"
    g.db.execute(query, {"access_token": access_token})
    g.db.commit()
    return '', 204


@app.route('/tweet/<int:tweet_id>', methods = ['GET'])
def get_tweets(tweet_id):
    
    query = """
        SELECT b.id, b.content, b.created, a.username
        FROM tweet b INNER JOIN user a on a.id = b.user_id
        WHERE b.id = :tweet_id
        """
    cursor = g.db.execute( query, {'tweet_id': tweet_id})
    db_result = cursor.fetchone()
    
    if db_result:
        result_dict = {
                'id': db_result[0],
                'content': db_result[1],
                'date': db_result[2].replace(' ','T'),
                'profile': "/profile/{}".format(db_result[3]),
                'uri': "/tweet/{}".format(tweet_id)
            }
        return make_response(json.dumps(result_dict), 200, {'Content-Type':JSON_MIME_TYPE})
    else:
        return '', 404 # no tweet found

@app.route('/tweet', methods = ['POST'])
@json_only
@auth_only
def post_tweets():
    access_token = request.get_json()['access_token']
    tweet_content = request.get_json()['content']
    query = "SELECT user_id FROM auth WHERE access_token = :access_token;"
    cursor = g.db.execute( query, {'access_token':access_token})
    db_result = cursor.fetchone()
    if not db_result:
        return abort(401)
    
    user_id = db_result[0]
    query = "INSERT INTO tweet (user_id, content) VALUES (:user_id, :tweet_content);"
    cursor = g.db.execute(query, {'user_id': user_id, 'tweet_content':tweet_content})
    g.db.commit()
    return '', 201 # tweet inserted

@app.route('/tweet/<int:tweet_id>', methods = ['DELETE'])
@auth_only
def delete_tweets(tweet_id):
    access_token = request.get_json()['access_token']
    query = "SELECT user_id FROM auth WHERE access_token = :access_token;"
    cursor = g.db.execute( query, {'access_token':access_token})
    db_result = cursor.fetchone()
    if not db_result:
        return abort(401)  # no authenticated user found;
        
    db_user_id = db_result[0]
    
    query = "SELECT user_id FROM tweet WHERE id = :tweet_id;"
    cursor = g.db.execute( query, {'tweet_id':tweet_id})
    db_result = cursor.fetchone()
    if not db_result:
        return abort(404) # no such tweet
    elif db_result[0] != db_user_id:
        return abort(401) # tweet doesn't belong to user
    
    query = "DELETE FROM tweet WHERE id = :tweet_id and user_id = :db_user_id;"
    cursor = g.db.execute(query, {'tweet_id' : tweet_id, 'db_user_id' : db_user_id})
    g.db.commit()
    return '',204 # tweet deleted

@app.errorhandler(404)
def not_found(e):
    return '',404


@app.errorhandler(401)
def not_found(e):
    return '',401
