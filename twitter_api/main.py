import sqlite3
import random
import string
import datetime

from flask import Flask, abort, g, request, Response
import json

try:
    from utils import *
except:
    from .utils import *

app = Flask(__name__)

def connect_db(db_name):
    return sqlite3.connect(db_name)

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


def create_token():
    characters = [ n for n in string.ascii_letters + string.digits]
    return "".join([random.choice(characters) for n in range(16)])


@app.route('/login', methods = ['POST'])
def login():
    request.data = json.loads(request.data.decode('utf-8'))
    password = request.data["password"] if "password" in request.data else None
    username = request.data["username"] if "username" in request.data else None
    
    if not password or not username:
        return abort(400)
        
    query = "SELECT id, password from user WHERE username=?"
    cursor = g.db.execute(query, (username, ))
    retrieved_data = cursor.fetchone()
    if retrieved_data:
        retrieved_user_id, retrieved_password  = retrieved_data
    
    if not retrieved_data or not retrieved_user_id: 
        return abort(404)
        
    if retrieved_password == md5(password.encode('utf-8')).hexdigest():
        token = create_token()
        datestamp = datetime.datetime.now().strftime("%Y-%m-%d")
        g.db.execute(
            "INSERT INTO auth (user_id, access_token, created) VALUES(?,?,?)",
            (retrieved_user_id, token, datestamp)
        )
        g.db.commit()
        
        return Response(
            json.dumps({"access_token":token}),
            201
        )
        
    else:
        abort(401)


@app.route('/profile/<username>')
def get_profile(username):
    
    user_query = "SELECT id, username, first_name, last_name, birth_date FROM user WHERE username = ?"
    user_cursor = g.db.execute(user_query, (username, ))
    retrieved_user = user_cursor.fetchone()
    
    if not retrieved_user:
        return abort(404)
    
    tweet_query = "SELECT id, user_id, created, content FROM tweet WHERE user_id = ?"
    tweet_cursor = g.db.execute(tweet_query, (retrieved_user[0], ))
    retrieved_tweet = tweet_cursor.fetchall()
    
    user_data = {
        "user_id": retrieved_user[0],
        "username": retrieved_user[1],
        "first_name": retrieved_user[2],
        "last_name": retrieved_user[3],
        "birth_date": retrieved_user[4],
        "tweet": [],
        "tweet_count": 0
    }
    for tweet in retrieved_tweet:
        user_data["tweet"].append({
            "date": tweet[2],
            "id": tweet[0],
            "text": tweet[3],
            "uri": "/tweet/{}".format(tweet[0])
        })
        user_data["tweet_count"] += 1
        
    return Response(json.dumps(user_data), content_type="application/json")


@app.route('/profile', methods = ['POST'])
@auth_only
#@json.only
def update_profile():
    request.data = json.loads(request.data.decode('utf-8'))
    if not "first_name" in request.data or not request.data["first_name"]: abort(400)
    
    if "access_token" in request.data and request.data['access_token']:
        query = "SELECT user_id FROM auth WHERE access_token = ?"
        cursor = g.db.execute(query, (request.data["access_token"], ) )
        user_id = cursor.fetchone()[0]
        
        query = "UPDATE user SET "
        
        for key, value in list(request.data.items())[:-1]:
            if key != "access_token":
                query += "{} = '{}', ".format(key, value)
            
        query += "{} = '{}' WHERE id = '{}'".format(
            list(request.data.items())[-1][0],
            list(request.data.items())[-1][1],
            user_id
        )
        
        g.db.execute(query)
        g.db.commit()
        
        return Response("Updated!", 201)
    else:
        abort(401)
                

@app.route('/tweet', methods = ['POST'])
@json_only
@auth_only
def post_tweet():
    payload = json.loads(request.data.decode('utf-8'))
    get_query = "SELECT user_id FROM auth WHERE access_token = ?"
    get_cursor = g.db.execute(get_query, (payload['access_token'], ))
    user = get_cursor.fetchone()[0]
    
    datestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    update_query = "INSERT INTO tweet (user_id, created, content) VALUES(?,?,?)"
    update_cursor = g.db.execute(update_query, (user, datestamp, payload['content']))
    g.db.commit()
    
    return Response("", 201)

#DELETE or VIEW tweets
@app.route('/tweet/<tweet_id>', methods = ["DELETE", "GET"])
def handle_tweet(tweet_id):
    query = "SELECT * FROM tweet WHERE id = ?"
    cursor = g.db.execute(query, (tweet_id, ))
    result = cursor.fetchone()
    
    if result:
        if request.method == 'GET':
            return get_tweet(result)
        else:
            return delete_tweet(tweet_id)
    else:
        abort(404)


def get_tweet(result):
    query = "SELECT username FROM user WHERE id = ?"
    cursor = g.db.execute(query, (result[1], ))
    user = cursor.fetchone()
    
    return Response(
        json.dumps({
            "date": result[2],
            "id": result[0],
            "content": result[3],
            "profile": "/profile/{}".format(user[0]),
            "uri": "/tweet/{}".format(result[0])
        }),
        content_type = 'application/json'
    )


#DELETE TWEET
@auth_only
def delete_tweet(tweet_id):
    token_owner_query = "SELECT user_id FROM auth WHERE access_token = ?"
    token_owner = g.db.execute(token_owner_query, (json.loads(request.data.decode('utf-8'))["access_token"] , ))
    token_owner = token_owner.fetchone()
    
    tweet_owner_query = "SELECT user_id from tweet WHERE id= ?"
    tweet_owner = g.db.execute(tweet_owner_query, (tweet_id, ))
    tweet_owner = tweet_owner.fetchone()
    
    if not tweet_owner == token_owner: return abort(401)
    
    query = "DELETE FROM tweet WHERE id = ?"
    g.db.execute(query, (tweet_id, ))
    g.db.commit()
    return Response("Deleted!", 204)
    

@app.route('/logout', methods =['POST'])
def logout():
    if "access_token" not in json.loads(request.data.decode('utf-8')): return abort(401)
    query = "SELECT access_token FROM auth WHERE access_token =?"
    cursor = g.db.execute(query, (json.loads(request.data.decode('utf-8'))["access_token"], ))
    
    if not cursor.fetchone():
        abort(401)
    
    del_query = "DELETE FROM auth WHERE access_token = ?"
    g.db.execute(del_query, (json.loads(request.data.decode('utf-8'))["access_token"], ))
    g.db.commit()
    return Response("Deleted!", 204)
    

@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
