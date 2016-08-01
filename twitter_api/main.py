import sqlite3

from flask import Flask
from flask import g
from utils import *
from flask import request
from flask import Response

#from hashlib import md5 #  temporary until we review the py 2 / py 3 task
import json
import random, string

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)
    
def _gen_access_token(user_id):
    token = ''.join(random.choice(string.ascii_uppercase + string.digits) for i in range(4))
    query = 'INSERT INTO "auth" (user_id, access_token) VALUES ("{}", "{}")'.format(user_id, token)
    g.db.execute(query)
    g.db.commit()
    return token
    
@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def unauth_request(e):
    return '', 401

@app.route('/login', methods=['GET', 'POST']) 
def login():
    if request.method == 'POST':
        # import ipdb;  ipdb.set_trace()
        data = json.loads(request.data)
        # print md5( data['password']) 
        if 'password' not in data:
            return 'Why u no password?',400
        cur = g.db.cursor()
        cur.execute('select id from user where username = "%s";' % data['username'])
        curresult = cur.fetchone()
        if not curresult:
            return "no such user",404 # shouldn't do this because of security issue but whatevs

        password =  md5(data['password']).hexdigest()# {u'username': u'demo', u'password': u'demo'} 
        cur = g.db.cursor()
        query = 'select id from user where username="{}" and password="{}";'.format(data['username'],password )
        # print command
        cur.execute(query)
        curresult = cur.fetchone()
        if not curresult:
            return "User login failed",401
        else:
            user_id = curresult[0]
            # token = _gen_access_token(user_id)
            
            
            return  json.dumps( {"access_token" : _gen_access_token(user_id) } ),201
            
        
        # print format(md5(data['password']).hexdigest()),data['password']
        return "Thanks!",200
    else:
        return "Please use Post",201


@app.route('/logout', methods=['POST']) 
def logout():
    data = json.loads(request.data)
        # print md5( data['password']) 
    if 'access_token' not in data:
        return 'Why u no access_token?',401
    # import ipdb;  ipdb.set_trace()
    
    #print data['access_token']
    query = 'DELETE FROM auth where access_token= "{}";'.format(data['access_token'])
    g.db.execute(query)
    g.db.commit()
    return "Logged out!",204 
    
    
def get_username_from_id(user_id):
    cur = g.db.cursor()
    query = 'select  username from user where id={};'.format(user_id )
    cur.execute(query)
    curresult = cur.fetchone()
    return curresult[0]

    
@app.route('/tweet/<int:tweet_id>', methods=['GET','POST','DELETE']) 
def tweet(tweet_id=None):    
    if request.method != 'GET':
        return 'Not implemented yet!',404
    else: # Get method
        print type(tweet_id)
        cur = g.db.cursor()
        query = 'select id,user_id,date(created)||"T"||time(created),content from tweet where id={};'.format(tweet_id )
        # print command
        cur.execute(query)
        curresult = cur.fetchone()
        if not curresult:
            return "Tweet-id doesn't exist, ya dingus!",404
        # print curresult
        
        tweetinfo =   dict({"id": curresult[0], "content" : curresult[3], "date" : curresult[2] , "profile": "/profile/"+get_username_from_id(curresult[1]), "uri" : '/tweet/'+str(tweet_id) })
        resp = Response(response=json.dumps(tweetinfo),    status=200,     mimetype="application/json")
        return(resp)
        
        
@app.route('/tweet/', methods=['GET','POST','DELETE']) 
def tweet_noparams(tweet_id=None):    
    return 'Not Implemented yet',404