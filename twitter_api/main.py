# -*- coding: utf-8 -*-
import sqlite3
import json
from .utils import *
from flask import Flask
from flask import g, request
import random
import string
from datetime import datetime, date, time

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401


@app.route('/login', methods = ['POST'])
@json_only
def login():
    data = request.get_json()
    
    if ('username' and 'password') not in data:
        return '', 400
    user_data = g.db.execute('select id, password from user where username = ?',[data['username']]).fetchone()
    if not user_data:
        return '', 404
    user_pwd = user_data[1]
    if user_pwd != md5(data['password']).hexdigest():
        return '', 401
    acc_tok = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    g.db.execute('INSERT INTO "auth" ("user_id", "access_token") VALUES (?, ?);',(user_data[0],acc_tok))
    g.db.commit()
    newdata = {
        "access_token":acc_tok
    }
    return json.dumps(newdata), 201, {'Content-Type': JSON_MIME_TYPE}

@app.route('/logout', methods = ['POST'])
@json_only
@auth_only
def logout():
    data = request.get_json()
    g.db.execute('delete from auth where access_token = ?',[data['access_token']]) 
    g.db.commit()
    return '', 204

@app.route('/tweet/<int:tweet_id>')
def get_tweet(tweet_id):
    query = """SELECT t.id, t.content, t.created, u.username
        FROM tweet t INNER JOIN user u ON u.id == t.id
        WHERE t.id=:tweet_id;
    """

    cursor = g.db.execute(query, {'tweet_id': tweet_id})
    tweet = cursor.fetchone()
    if tweet is None:
        #abort(404)
        return '', 404

    t_id, content, dt, username = tweet
    dt_formatted = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").isoformat()
    data = {
        "id": t_id,
        "content": content,
        "date": dt_formatted,
        "profile": "/profile/%s" % username,
        "uri": "/tweet/%s" % t_id
    }
    return json.dumps(data), 200, {'Content-Type': JSON_MIME_TYPE}

@app.route('/tweet', methods = ['POST'])
@json_only
@auth_only
def post_tweet():
    data = request.get_json()
    user_data = g.db.execute('select user_id from auth where access_token = ?',[data['access_token']]).fetchone()
    user_id = user_data[0]
    g.db.execute('insert into "tweet" ("user_id","content") VALUES (?,?)',(user_id,data['content']))
    g.db.commit()
    return '', 201

@app.route('/tweet/<int:tweet_id>', methods = ['DELETE'])
@json_only
@auth_only
def delete_tweet(tweet_id):
    valid_tweets = g.db.execute('select id, user_id from tweet').fetchall()
    valid_tweetids = [x[0] for x in valid_tweets]

    if tweet_id not in valid_tweetids:
        return '', 404
    data = request.get_json()
    user_data = g.db.execute('select user_id from auth where access_token = ?',[data['access_token']]).fetchone()
    user_id = user_data[0]
    if (tweet_id, user_id) not in valid_tweets:
        return '', 401
    g.db.execute('delete from "tweet" where id = ?',[tweet_id])
    g.db.commit()
    return '', 204

@app.route('/profile/<username>')
def get_profile(username):
    user_data_u = g.db.execute('select * from user where username = ?', [username]).fetchone()
    if not user_data_u:
        return '', 404
    user_data = _unicode_to_str(user_data_u)
    print(user_data)
    tweet_data = g.db.execute('select * from tweet where user_id = ?',[user_data[0]]).fetchall()

    user_tweets =[]
    for tweet_u in tweet_data:
        tweet = _unicode_to_str(tweet_u)
        t_id, text, dt = tweet[0],tweet[3],tweet[2]
        dt_formatted = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").isoformat()
        user_tweets.append( {
            "date": dt_formatted,
            "id": t_id,
            "text": text,
            "uri": "/tweet/%s" % t_id
        })
    u_id, u_name, u_pwd, u_fname, u_lname, u_bdate = user_data[0],user_data[1],user_data[2],user_data[3],user_data[4],user_data[5]
    data = {
        'user_id': u_id,
        'username': u_name,
        'first_name': u_fname,
        'last_name': u_lname,
        'birth_date': u_bdate,
        'tweets': user_tweets,
        'tweet_count': len(user_tweets),
    }
    return json.dumps(data), 200, {'Content-Type': JSON_MIME_TYPE}

def _unicode_to_str(data):
    new_data = []
    for x in data:
        if isinstance(x,int):
            new_data.append(x)
        elif not x:
            new_data.append(x)
        else:
            new_data.append(str(x))
    return new_data

@app.route('/profile', methods = ['POST'])
@json_only
@auth_only
def post_profile():
    data = request.get_json()
    if 'access_token' not in data:
        return '', 400
    if 'first_name' not in data:
        return '', 400
    if 'last_name' not in data:
        return '', 400
    if 'birth_date' not in data:
        return '', 400
    user_data = g.db.execute('select user_id from auth where access_token = ?',[data['access_token']]).fetchone()
    user_id = user_data[0]
    g.db.execute("update user set 'first_name' = ?, 'last_name' = ?, 'birth_date' = ? where id = ?",\
                   (data['first_name'], data['last_name'], data['birth_date'], user_id))
    g.db.commit()
    return '', 201