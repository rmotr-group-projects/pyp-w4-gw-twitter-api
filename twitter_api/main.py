import sqlite3

from flask import Flask, request, session, g, jsonify, abort

from .utils import md5, make_token, json_only, auth_only

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here
@app.route('/login', methods = ['POST'])
def login():
    username = request.json['username'] 
    try:
        password = md5(request.json['password'].encode('utf-8')).hexdigest()
    except KeyError:
        abort(400)
    cursor = g.db.execute(
        "SELECT id, password FROM user WHERE username=:username;",
        {'username':username})
    
    
    user = cursor.fetchone()
    if user is None:
        abort(404)
    if password != user[1]:
        abort(401)
    if user:
        query = "INSERT INTO auth ('user_id', 'access_token') VALUES(:user_id, :access_token);"
        acc_token = md5(make_token(12)).hexdigest()
        params = {'user_id': user[0], 'access_token':acc_token}
        g.db.execute(query,params)
        g.db.commit()
        return jsonify(access_token=acc_token), 201


@app.route('/logout', methods = ['POST'])
def logout():
    try: 
        access_token = request.json['access_token']
    except KeyError:
        abort(401)
    cursor = g.db.execute('SELECT access_token FROM auth where access_token=:access_token;', {'access_token':access_token})
    authdb = cursor.fetchone()
    if authdb:
        g.db.execute('DELETE FROM auth WHERE access_token=:access_token;', {'access_token':access_token})
        g.db.commit()
        return "", 204
            
@app.route('/profile/<USERNAME>')   
def public_profile(USERNAME):
    cursor = g.db.execute("""
    SELECT * FROM user
    WHERE username=:username;""",{'username': USERNAME})
    
    _profile = cursor.fetchone()
    
    if not _profile:
        abort(404)
    
    t_cursor = g.db.execute(
        "SELECT id, content, created FROM tweet WHERE user_id=:user_id;",
        {'user_id': _profile[0]}
        )
    
    _tweets = t_cursor.fetchall()
    
    params = {
  "user_id": _profile[0],
  "username": _profile[1],
  "first_name": _profile[3],
  "last_name": _profile[4],
  "birth_date": _profile[5],
  "tweets": [{"id": t[0],
        "text": t[1],
        "date": t[2].replace(" ", "T"),
        "uri": '/tweet/{}'.format(t[0])} for t in _tweets],
  "tweet_count": len(_tweets)}
    
    return jsonify(params)
        
@app.route('/profile', methods = ['POST'])
@json_only
@auth_only
def profile():
   
    query = """UPDATE user
    SET first_name=:first_name, last_name=:last_name, birth_date=:birth_date 
    WHERE id=(SELECT user_id FROM auth WHERE access_token=:access_token);
    """
    
    try: params = {'first_name':request.json['first_name'], 'last_name':request.json['last_name'],
    'birth_date':request.json['birth_date'], 'access_token':request.json['access_token']}
    except KeyError:
        abort(400)
    g.db.execute(query,params)
    g.db.commit()
    return '', 201

@app.route('/tweet/<TWEET_ID>')
def get_tweet(TWEET_ID):
    cursor = g.db.execute('SELECT t.id, t.content, t.created, u.username from tweet t, user u where t.id=:tweet_id AND t.user_id = u.id;',{'tweet_id':TWEET_ID})
    tweet = cursor.fetchone()
    if not tweet:
        abort (404)
    params = {
        "id": tweet[0],
        "content": tweet[1],
        "date": tweet[2].replace(" ", "T"),
        "profile": "/profile/{}".format(tweet[3]),
        "uri": "/tweet/{}".format(tweet[0])
        }
    
    return jsonify(params)

@app.route('/tweet', methods = ['POST'])
@json_only
@auth_only
def post_tweet():
    query = 'INSERT INTO tweet(user_id, content) VALUES ((SELECT user_id from auth WHERE access_token=:access_token), :content);' 
    try: 
        params = {'access_token': request.json['access_token'], 'content': request.json['content']}
    except KeyError:
        abort(401)
    g.db.execute(query,params)
    g.db.commit()
    return '', 201
    
@app.route('/tweet/<TWEET_ID>', methods = ['DELETE'])
@auth_only
@json_only
def delete_tweet(TWEET_ID):
    
    cursor = g.db.execute('SELECT id, user_id from tweet where id=:tweet_id;', {'tweet_id':TWEET_ID})
    if not cursor.fetchone():
        abort(404)
    
    cursor_user = g.db.execute("""
    SELECT id FROM tweet 
    where user_id=(SELECT user_id from auth where access_token=:access_token)
    AND id=:tweet_id;""",
    {'access_token': request.json['access_token'], 'tweet_id':TWEET_ID})
    
    if not cursor_user.fetchone():
        abort (401)
    
    g.db.execute('DELETE from tweet where id=:tweet_id;', {'tweet_id':TWEET_ID})
    g.db.commit()
    return '', 204
        
    
@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
