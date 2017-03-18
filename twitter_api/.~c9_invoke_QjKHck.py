import sqlite3
import random
import string
import datetime

from flask import Flask, abort, g, request, Response
import json

from utils import *

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
    request.data = json.loads(request.data)
    password = request.data["password"] if "password" in request.data else None
    username = request.data["username"] if "username" in request.data else None
    
    if not password or not username:
        return abort(400)
        
    query = "SELECT id, password from user WHERE username=?"
    cursor = g.db.execute(query, (username, ))
    retrieved_user_id, retrieved_password = cursor.fetchone()
    
    if not retrieved_user_id: 
        return abort(404)
        
    if retrieved_password == md5(password).hexdigest():
        token = create_token()
        datestamp = datetime.datetime.now().strftime("%Y-%m-%d")
        g.db.execute(
            "INSERT INTO auth (user_id, access_token, created) VALUES(?,?,?)",
            (retrieved_user_id, token, datestamp)
        )
        g.db.commit()
        return token
        
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
#@auth_only()
#@json.only()
def update_profile():
    if not "first_name"
    if not "first_name" in request.data or not request.data["first_name"]: abort(400)
    
    if "access_token" in request.data and request.data['access_token']:
        query = "SELECT user_id FROM auth WHERE access_token = ?"
        cursor = g.db.execute(query, (request.data["access_token"], ) )
        user_id = cursor.fetchone()[0]
        
        query = "UPDATE user SET "
        
        for key, value in request.data.items()[:-1]:
            if key != "access_token":
                query += "{} = '{}', ".format(key, value)
            
        query += "{} = '{}' WHERE id = '{}'".format(
            request.data.items()[-1][0],
            request.data.items()[-1][1],
            user_id
        )
        
        g.db.execute(query)
        g.db.commit()
        
        return Response("Updated!", 201)
    else:
        abort(401)
                

@app.route('/tweet', methods = ['POST'])
# @auth.only
#CREATE TWEET
def post_tweet():
    # post success 201
    pass

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
            "text": result[3],
            "profile": "/profile/{}".format(user[0]),
            "uri": "/tweet/{}".format(result[0])
        }),
        content_type = 'application/json'
    )


#DELETE TWEET
@auth_only
def delete_tweet(tweet_id):
    query = "SELECT * FROM tweet WHERE id = ?"
    cursor = g.db.execute(query, (tweet_id, ))
    # make sure tweet trying to delete belongs to the same auth user (this may already be done by @dec)
    # check if the tweet exists, if not, 404
    # success 204
    pass


@app.route('/logout', methods =['POST'])
def logout(access_token):
    #check if user is logged in (token)
    #cursor = self.db.execute("select * from auth where user_id = ?")
    #if no fetch result, return 401
    #else return 201 and delete from auth
    pass


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
