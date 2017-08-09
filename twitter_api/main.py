import json
import sqlite3
from datetime import datetime

from flask import Flask
from flask import Response, abort, request
from flask import g

from twitter_api.utils import (md5, create_token, auth_only, json_only)

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here
def query_db(query, args=(), one=False):
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv


def get_user_id_from_token(token):
    user = query_db('select user_id from auth where access_token=?', [token], one=True)
    return user['user_id'] if user else None


@app.route('/login', methods=['POST'])
def login():
    if request.data:
        # retrieve post values
        data = request.get_json()
        username = data.get('username', None)
        password = data.get('password', None)

        # check if post info is complete
        if username and password:
            user = query_db('select * from user where username=?', [username], one=True)

            # check if the user exists
            if user:
                if user['password'] != md5(password).hexdigest():
                    # wrong password
                    abort(401)

                # check if they are logged in. don't generate duplicate token
                token = query_db('select * from auth where user_id=?', [user['id']], one=True)

                if not token:
                    # generate the token
                    query_db('insert into auth (user_id, access_token) values(?, ?)',
                             [user['id'], create_token()])
                    g.db.commit()
                    # retrieve token
                    token = query_db('select * from auth where user_id=?', [user['id']], one=True)

                resp = {"access_token": token['access_token']}
                resp = Response(response=json.dumps(resp), status=201, mimetype="application/json")
                return resp
            else:
                # user not found
                abort(404)
    # user did not provide username and password
    abort(400)


@app.route('/logout', methods=['POST'])
@auth_only
def logout(*args, **kwargs):
    access_token = request.get_json()['access_token'] if request.get_json() else abort(401)
    query_db('delete from auth where access_token=?', [access_token])
    g.db.commit()
    return Response(response='', status=204)


@app.route('/profile/<username>')
def get_profile(username):
    profile = query_db('select id as user_id, username, first_name, last_name, birth_date '
                       'from user where username=?',
                       [username],
                       one=True)
    if profile:
        tweets = query_db('select id, content as text, created as date from tweet where user_id=?',
                          [profile['user_id']])
        for t in tweets:
            t['uri'] = '/tweet/{}'.format(t['id'])
            created_date = datetime.strptime(t['date'], '%Y-%m-%d %H:%M:%S')
            t['date'] = created_date.strftime("%Y-%m-%dT%H:%M:%S")
        profile['tweet_count'] = len(tweets)
        profile['tweets'] = tweets

        return Response(response=json.dumps(profile), status=200, mimetype="application/json")

    return abort(404)


@app.route('/profile', methods=['POST'])
@auth_only
@json_only
def post_profile():
    required_attrs = ['first_name', 'last_name', 'birth_date']
    data = request.get_json()
    user_id = get_user_id_from_token(data['access_token'])
    if not user_id:
        abort(401)
    if all(attr in data for attr in required_attrs):
        query_db('update user set first_name=?, last_name=?, birth_date=? where id=?',
                 (data['first_name'], data['last_name'],
                  data['birth_date'],
                  int(user_id)))
        g.db.commit()
        return Response(response='', status=201)
    abort(400)


@app.route('/tweet/<tweet_id>')
def get_tweet(tweet_id):
    tweet = query_db('select t.id, t.content, t.created as date, u.username as profile '
                     'from tweet t inner join user u on t.user_id = u.id '
                     'where t.id=?', [tweet_id], one=True)
    if tweet:
        created_date = datetime.strptime(tweet['date'], '%Y-%m-%d %H:%M:%S')
        tweet['date'] = created_date.strftime("%Y-%m-%dT%H:%M:%S")
        tweet['profile'] = '/profile/{}'.format(tweet['profile'])
        tweet['uri'] = '/tweet/{}'.format(tweet['id'])

        return Response(response=json.dumps(tweet), status=200, mimetype='application/json')

    abort(404)


@app.route('/tweet', methods=['POST'])
@auth_only
@json_only
def post_tweet():
    required_attrs = ['content']
    data = request.get_json()
    user_id = get_user_id_from_token(data['access_token'])
    if not user_id:
        abort(401)
    if all(attr in data for attr in required_attrs):
        query_db('insert into tweet (user_id, content) values(?, ?)',
                 (user_id, data['content']))
        g.db.commit()
        return Response(response='', status=201)
    abort(400)


@app.route('/tweet/<tweet_id>', methods=['DELETE'])
@auth_only
@json_only
def delete_tweet(tweet_id):
    data = request.get_json()
    tweet = query_db('select id, user_id '
                     'from tweet '
                     'where id=?', [tweet_id], one=True)
    if tweet:
        if tweet['user_id'] == get_user_id_from_token(data['access_token']):
            query_db('delete from tweet where id=?', [tweet_id])
            g.db.commit()

            return Response(response='', status=204)
        else:
            # tweet does not belong to user
            abort(401)

    abort(404)


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
