import sqlite3
import json
from flask import Flask, Response, abort, request
from flask import g
from .utils import JSON_MIME_TYPE, md5, auth_only, retrieve_resource, get_user_from_token, json_only
from datetime import datetime
import random
import hashlib

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def rename_dict_key(dict, old_key_name, new_key_name):
    dict[new_key_name] = dict[old_key_name]
    del dict[old_key_name]

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])
    #db.row_factory = sqlite3.Row
    g.db.row_factory = dict_factory
# implement your views here
@app.route('/tweet')
def tweet_list():
    curs = g.db.cursor()
    curs.execute("SELECT * from tweet")
    tweets = curs.fetchall()
    return Response(json.dumps(tweets), 200, mimetype=JSON_MIME_TYPE)

@app.route('/profile', methods=['POST'])
@json_only
@auth_only
def update_profile():
    req = request.get_json()
    if not ('first_name' in req and 'last_name' in req and 'birth_date' in req):
        abort(400)
    print("update_profile ***********")
    user_id_list = retrieve_resource("auth","user_id", access_token=req['access_token'])
    
    curs = g.db.cursor()
    curs.execute("UPDATE user SET first_name = :first_name, last_name = :last_name, birth_date = :birth_date where id = :user_id", {'first_name' : req['first_name'], 'last_name' : req['last_name'], 'birth_date' : req['birth_date'], 'user_id' : user_id_list[0]['user_id']})
    g.db.commit()
    return Response('', 202)



@app.route('/tweet/<int:tweet_id>')
def tweet_detail(tweet_id):
    
    tweet = retrieve_resource("tweet",id=tweet_id)
    print ("tweet_detail:" + str(tweet))
    if not tweet:
        return abort(404)
    tweet = tweet[0]    
    profile_id = tweet['user_id']
    profile_resc = retrieve_resource("user","username", id=profile_id)[0]
    print (profile_resc)
    profile_username = profile_resc["username"]
    tweet['profile'] = '/profile/' + profile_username
    del tweet['user_id']
    tweet['uri'] = '/tweet/' + str(tweet['id'])
    rename_dict_key(tweet, 'created', 'date')
    dt = datetime.strptime(tweet['date'], "%Y-%m-%d %H:%M:%S")
    tweet['date'] = dt.isoformat()
    #tweet['created'] = datetime.datetime(tweet['created'])
    return Response(json.dumps(tweet), 200, mimetype=JSON_MIME_TYPE)

@app.route('/profile/<username>')
def profile_list(username):
    profiles = retrieve_resource("user",username=username)
    print("profiles----" + str(profiles))
    if not profiles:
        abort(404)
    profile = profiles[0]
    #profile = search_resource("user", "username", username)
    tweets = retrieve_resource("tweet", user_id=profile['id'])
    for t in tweets:
        t['uri'] = "/tweet/" + str(t['id'])
        del t['user_id']
        rename_dict_key(t, "content", "text")
        rename_dict_key(t, "created", "date")
        dt = datetime.strptime(t['date'], "%Y-%m-%d %H:%M:%S")
        t['date'] = dt.isoformat()
    

    profile['tweets'] = tweets
    profile['tweet_count'] = len(tweets)
    del profile['password']
    rename_dict_key(profile, "id", "user_id")
    
    if profile is None:
        abort(404)
    print ("profile***: " +str(profile))
    return Response(json.dumps(profile, sort_keys=True), 200, mimetype=JSON_MIME_TYPE)

def generate_token():
    m = hashlib.sha1()
    m.update(str(random.randint(-10000000,100000000)).encode(('UTF-8')))
    return m.hexdigest()
    
@app.route('/login', methods=['POST'])
@json_only
def login():
    credentials = request.get_json()
    if not ('password' in credentials and 'username' in credentials):
        abort(400)
    supplied_password = md5(credentials['password']).hexdigest()
    curs = g.db.cursor()
    curs.execute("SELECT id, password from user where username=:username", credentials)
    row = curs.fetchall()
    if len(row) == 1:
        row = row[0]
        if row['password'] == supplied_password:
            user_id = row['id']
            token = generate_token()
            insert = "INSERT INTO auth (user_id, access_token) VALUES (:user_id, :token)"
            curs.execute(insert, {'user_id': user_id, 'token': token})
            g.db.commit()
            token_dict = {'access_token': token}
            return Response(json.dumps(token_dict), 201, mimetype=JSON_MIME_TYPE)
        else:
            return abort(401)
    else:
        abort(404)

@app.route('/logout', methods=["POST"])
@json_only
def logout():
    req = request.get_json()
    if 'access_token' in req:
        received_token = req['access_token']
        curs = g.db.cursor()
        curs.execute("DELETE from auth where access_token = :access_token", {'access_token' : received_token})
        g.db.commit()
        return Response("", 204)
    else:
        abort(401)
        
@app.route('/tweet', methods=['POST'])
@json_only
@auth_only
def create_tweet():
    req = request.get_json()
    user_id = get_user_from_token(req, 'access_token')
    print ("user_id in CREATE_TWEET: " + str(user_id))
    curs = g.db.cursor()
    curs.execute("INSERT INTO tweet (user_id, content) VALUES (:user_id, :content)", {'user_id' : user_id['user_id'], 'content' : req['content']})
    g.db.commit()
    return Response('', 201, mimetype=JSON_MIME_TYPE)


@app.route('/tweet/<int:tweet_id>', methods=['DELETE'])
@auth_only
@json_only
def delete_tweet(tweet_id):
    req = request.get_json()
    user_id = get_user_from_token(req, 'access_token')
    print("userID###" + str(user_id))
    tweet = retrieve_resource('tweet', 'user_id', id=tweet_id)
    if tweet:
        if user_id['user_id'] != tweet[0]['user_id']:
            abort(401)
        curs = g.db.cursor()
        curs.execute("DELETE from tweet WHERE id = :id", {'id' : str(tweet_id)})
        g.db.commit()
        return Response('', 204, mimetype=JSON_MIME_TYPE)
    else:
        abort(404)


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
