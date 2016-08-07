import sqlite3
import json
from flask import Flask, g, jsonify, abort, request, Response
from .utils import app, md5, connect_db, before_request, JSON_MIME_TYPE, auth_only, json_only, check_login



# ---- LOGIN ---- #
@app.route('/login', methods = ['POST'])
@json_only
@check_login
def login(usr_id = None, access_token = None):
    resp = {'access_token': access_token}
    g.db.execute('INSERT INTO auth (user_id, access_token) VALUES (?, ?)',
                                                (usr_id,access_token))
    g.db.commit()
    resp = json.dumps(resp)
    return Response(resp, status=201)
# ---- LOGIN ---- #


# ---- LOGOUT ---- #
@app.route('/logout', methods = ['POST'])
@json_only
def logout():
    info = request.json
    if not 'access_token' in info.keys():
        abort(401)
    g.db.execute('DELETE FROM auth WHERE access_token = ?',
                                        (info['access_token'],))
    g.db.commit()
    return Response(status=204)
# ---- LOGOUT ---- #


# ---- PROFILE ---- #
@app.route('/profile', methods = ['POST'])
@auth_only
@json_only
def change_profile():
    info = request.json
    req_fields = ['first_name', 'last_name', 'birth_date']
    if not all(field in info for field in req_fields):
        abort(400)
    # the access_token is valid, no need to check if user_id is None
    user_id = g.db.execute('SELECT user_id from auth WHERE access_token = ?',
                          (info['access_token'],)).fetchone()[0]
    for field in req_fields:
        g.db.execute('UPDATE user SET {} = ? WHERE id = ?'.format(field),
                    (str(info[field]),user_id))
    g.db.commit()
    return Response(status=201)


@app.route('/profile/<username>', methods = ['GET'])
def fetch_profile(username):
    user_info = g.db.execute('SELECT id, username, first_name, last_name, \
                            birth_date FROM user WHERE username = ?',
                (username,)).fetchone()
    if not user_info:
        abort(404)
    fields = ['user_id', 'username', 'first_name', 'last_name', 'birth_date']
    user = {field:user_info[index] for index, field in enumerate(fields)}
    
    tweets = g.db.execute('SELECT id, created, content from tweet WHERE user_id = ?',
              (user['user_id'],)).fetchall()
    fmt_tweets = []

    for tweet in tweets:
        tw_id, date, text, uri = tweet + ('/tweet/{}'.format(str(tweet[0])),)
        fmt_tweet = {'date': date, 'id': tw_id, 'text': text, 'uri': uri}
        fmt_tweet['date'] = fmt_tweet['date'].replace(' ','T')
        fmt_tweets.append(fmt_tweet)
    user['tweet'] = fmt_tweets
    user['tweet_count'] = len(tweets)
    resp = json.dumps(user)
    return Response(resp, status=200, mimetype=JSON_MIME_TYPE)
# ---- PROFILE ---- #

# ---- TWEET ----- #
@app.route('/tweet/<int:tweet_id>', methods = ['GET'])
def fetch_tweet(tweet_id):
    tweet = g.db.execute('SELECT id, content, created, user_id \
                        FROM tweet WHERE id = ?', (tweet_id,)).fetchone()
    if not tweet:
        abort(404)

    tweet = list(tweet)
    tweet_id, user_id = tweet[0], tweet.pop(3) # don't need the user id any more
    profile = g.db.execute('SELECT username from user WHERE id = ?',
                         (user_id,)).fetchone()[0]
    profile = '/profile/{}'.format(profile)
    uri = '/tweet/{}'.format(tweet_id)
    tweet += [profile,uri]
    resp = zip(['id', 'content', 'date', 'profile', 'uri'], tweet)
    resp = {key: value for key, value in resp}
    resp['date'] = resp['date'].replace(' ','T')
    resp = json.dumps(resp)
    return Response(resp, status=200, mimetype=JSON_MIME_TYPE)

@app.route('/tweet/<int:tweet_id>', methods = ['DELETE'])
@auth_only
@json_only
def delete_tweet(tweet_id):
    user_id = g.db.execute('SELECT user_id from auth WHERE access_token = ?',
                         (request.json['access_token'],)).fetchone()
    req_id = g.db.execute('SELECT user_id from tweet WHERE id = ?',
                        (tweet_id,)).fetchone()
    
    if not req_id: # tweet doesn't exist
        abort(404)
    if user_id != req_id:
        abort(401)

    g.db.execute('DELETE from tweet WHERE id = ?', (tweet_id,))
    g.db.commit()
    return Response(status=204)


@app.route('/tweet', methods = ['POST'])
@auth_only
@json_only
def post_tweet():
    if not 'content' in request.json.keys():
        abort(401)
    user_id = g.db.execute('SELECT user_id FROM auth WHERE access_token = ?',
              (request.json['access_token'],)).fetchone()[0]
    g.db.execute('INSERT INTO tweet (user_id, content) VALUES (?, ?)',
                (user_id, request.json['content']),)
    g.db.commit()
    return Response(status=201)
# ---- TWEET ----- #


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
