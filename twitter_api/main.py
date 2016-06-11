import sqlite3
from .utils import json_only
from flask import Flask, jsonify
from flask import g, request, abort
from hashlib import md5
from datetime import datetime
import json


app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here

def _md5_hash(pw):
    return md5(pw).hexdigest()


@app.route('/login', methods=['POST'])
def login():
    #Accept json with username and pw
    #return acces token
    if  'password' not in request.json or 'username' not in request.json:
        abort(400)
    
    user = request.json['username']
    received_password = request.json['password']
    
    cursor = g.db.execute("SELECT id, password FROM user WHERE username IS ?", (user,))
    fetched_data = cursor.fetchone()
    
    if not fetched_data:
        abort(404)
    
    user_id, password = fetched_data
    if _md5_hash(received_password) == password:
        #generate auth-token and return it
        
        #generate access token
        now = str(datetime.now())
        access_token = _md5_hash(user+received_password+now)
        #insert to auth table
        g.db.execute('INSERT INTO "auth" ("user_id", "access_token", "created") VALUES (?, ?, ?)', (user_id, access_token, now))
        g.db.commit()
        #return access token
        dict_for_json = {"access_token" : access_token}
        return json.dumps(dict_for_json), 201
    else:
        abort(401)
        
        
    
@app.route('/logout', methods=['POST'])
def logout():
    if 'access_token' not in request.json:
        abort(401)
        
    token = request.json['access_token']
    g.db.execute('DELETE FROM "auth" WHERE access_token = ?', (token,))
    g.db.commit()
    return ('', 204)


@app.route('/profile/<username>', methods = ['GET'])
def get_profile(username):
    cursor = g.db.execute('SELECT id, username, first_name, last_name, birth_date FROM user WHERE username = ?',(username,))
    
    vals = cursor.fetchone()
    
    if not vals:
        abort(404)
        
    cols = ["user_id", "username", "first_name", "last_name", "birth_date"]
    data = dict(zip(cols, vals))
    cursor = g.db.execute('SELECT  id, content, created FROM tweet WHERE user_id = ? ORDER BY id asc',(data['user_id'],))
    tweets = [dict(id=row[0], text=row[1], date=row[2], uri="/tweet/" + str(row[0])) for row in cursor.fetchall()]
    data["tweet"] = tweets
    data["tweet_count"] = len(tweets)
    
    return jsonify(data)
    


@app.route('/profile', methods = ['POST'])
@json_only
def update_profile():
    fields = set(['first_name', 'last_name', 'birth_date'])
    
    if fields.intersection(request.json.keys()) != fields:
        abort(400)
        
    if "access_token" not in request.json.keys():
        abort(401)
   
    
    fn = request.json['first_name']
    ln = request.json['last_name']
    bd = request.json['birth_date']
    token = request.json['access_token']
    
    user_id = _find_user_id_by_token(token)
    
    g.db.execute("UPDATE user SET first_name=?, last_name=?, birth_date=? WHERE id=?", (fn, ln, bd, user_id))
    g.db.commit()
    
    return('', 201)

def _find_user_id_by_token(token):
    cursor = g.db.execute("SELECT user_id FROM auth WHERE access_token=?", (token,))
    return_val = cursor.fetchone()
    if not return_val:
        abort(401)
    return return_val[0]
    


    
    
@app.route('/tweet/<tweet_id>', methods = ['GET'])
@json_only
def get_tweet(tweet_id):
    cursor = g.db.execute('SELECT t.id,  t.content, t.created, "/profile/" || u.username, "/tweet/" || t.id FROM tweet t LEFT JOIN user u ON u.id = t.user_id WHERE t.id=?',(tweet_id,))
    vals = cursor.fetchone()
    
    if not vals:
        abort(404)
    """
    {
      "id": <TWEET-ID>,
      "text": "Tweet test",
      "date": "2016-12-31T00:30:19",
      "profile": "/profile/<USERNAME>",
      "uri": "/tweet/<TWEET-ID>"
    }
    """
    cols = ["id", "content", "date", "profile", "uri"]
    data = dict(zip(cols, vals))
    
    return jsonify(data)




@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
