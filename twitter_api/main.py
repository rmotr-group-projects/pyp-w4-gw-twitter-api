import sqlite3
import json
from flask import (Flask, g, request, abort, Response, jsonify)
import random
from .utils import md5


app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here

@app.route('/login', methods=['POST'])
def login():
    if not request.json or not 'username' in request.json or not 'password' in request.json:
        abort(400)
    username = request.json.get('username', "")
    password = request.json.get('password', "")
    check_user = username_password(username, password)
    if not check_user[0]:
        abort(404)
    if not check_user[1]:
        abort(401)
    token = random.SystemRandom().random()
    access_token={
                "access_token": str(token),
                }
    user_id = convert_username_to_id(username)
    insert_token(user_id, access_token['access_token'])
    return json.dumps(access_token), 201

@app.route('/logout', methods=['POST'])
def logout():
    if not request.json or not 'access_token' in request.json:
        abort(401)
    token = request.json.get('access_token')
    curs = g.db.execute('SELECT * FROM auth')
    data = curs.fetchall()
    for x in data:
        if token in x:
            id = x[0]
    g.db.execute('DELETE FROM auth WHERE id=%s' % id)
    g.db.commit()
    return '', 204

@app.route('/profile/<name>')
def get_profile(name):
    user = find_user(name)
    if not user:
        abort(404)
    user_id = user['user_id']
    tweets = get_user_tweets(user_id)
    user['tweets'] = tweets
    result = json.dumps(user)
    return Response(result, content_type='application/json')

@app.route('/profile', methods=["POST"])
def profile():
    if not request.json or not 'first_name' in request.json or not 'last_name' in request.json:
        abort(400)
    token = request.json.get('access_token', '')
    user_id = valid_token(token)
    if not 'access_token' in request.json or not user_id:
        abort(401)
    first_name = request.json.get('first_name', '')
    last_name = request.json.get('last_name', '')
    birth_date = request.json.get('birth_date', '')
    g.db.execute('UPDATE user SET first_name="%s", last_name="%s", birth_date="%s" WHERE id=%s' % (first_name, last_name, birth_date, user_id))
    g.db.commit()
    return '', 201

@app.route('/tweet/<id>', methods=['GET', 'DELETE'])
def get_tweet(id):
    if request.method =='DELETE':
        if not valid_token(request.json.get('access_token', '')):
            abort(401)
        valid_tweet = valid_tweet_id(id)
        if not valid_tweet:
            abort(404)
        if not valid_token(request.json.get('access_token', '')) == valid_tweet[1]:
            abort(401)
        g.db.execute('DELETE FROM tweet WHERE id=%s' % id)
        g.db.commit()
        return '', 204
    valid_tweet = valid_tweet_id(id)
    if not valid_tweet:
        abort(404)
    username = get_username_from_id(valid_tweet[1])######
    a_dict = dict(id=valid_tweet[0], content=valid_tweet[3], date=valid_tweet[2], profile='/profile/'+username, uri='/tweet/'+str(id))
    result = json.dumps(a_dict)
    return Response(result, content_type='application/json')

@app.route('/tweet', methods=['POST'])
def post_tweet():
    if not request.json:
        abort(400)
    user_id = valid_token(request.json.get('access_token',''))
    if not user_id or not 'access_token' in request.json:
        abort(401)
    content = request.json.get('content', '')
    g.db.execute('INSERT INTO tweet (user_id, content) VALUES (%s, "%s")' % (user_id, content))
    g.db.commit()
    return '', 201





#helper functions
def get_username_from_id(user_id):
    cur = g.db.execute('SELECT username FROM user WHERE id=%s' % user_id)
    name = cur.fetchone()[0]
    return name

def valid_tweet_id(tweet_id):
    '''returns a whole tweet'''
    print (type(tweet_id))
    cur = g.db.execute('SELECT * FROM tweet')
    data = cur.fetchall()
    print(data)
    for x in data:
        if int(tweet_id) == x[0]:
            return x


def valid_token(token):
    '''if valid returns user ID'''
    curs = g.db.execute('SELECT * FROM auth')
    data = curs.fetchall()
    for x in data:
        if token in x:
            return x[1]
    return False

def find_user(name):
    cur = g.db.execute('SELECT id, username, first_name, last_name, birth_date FROM user')
    data = cur.fetchall()
    for x in data:
        if name in x:

            return dict(user_id=x[0], username=x[1], first_name=x[2], last_name=x[3], birth_date=x[4])



def get_user_tweets(user_id):
    cur = g.db.execute('SELECT * FROM tweet WHERE user_id=%s' % user_id)
    data = cur.fetchall()
    arr = []
    for x in data:
        a_dict = dict(id=x[0], text=x[3], date=x[2], uri='/tweet/'+str(x[0]))
        arr.append(a_dict)
    return arr

def username_password(username, password):
    curs = g.db.execute('SELECT * FROM user')
    data = curs.fetchall()
    arr = []
    for x in data:
        if username in x:
            arr.append(1)
            if md5(password).hexdigest() in x:
                arr.append(1)
            else:
                arr.append(0)
    if not arr:
        arr = [0, 0]
    return arr

def insert_token(user_id, token):
    curs = g.db.execute('INSERT INTO auth (user_id, access_token) VALUES (%s, "%s")'%(user_id, token))
    g.db.commit()
    curs = g.db.execute('select * from auth')

def convert_username_to_id(username):
    users_cursor = g.db.execute('SELECT * FROM user')
    users_data = users_cursor.fetchall()
    for x in users_data:
        if username in str(x):
            return x[0]



@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
