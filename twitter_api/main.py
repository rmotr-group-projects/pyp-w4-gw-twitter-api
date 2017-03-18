import sqlite3

from flask import Flask
from flask import g
from .utils import *
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
        
 
        data = json.loads(str(request.data.decode('utf-8')))
      
        # print md5( data['password']) 
        if 'password' not in data:
            return 'Why u no password?',400
        cur = g.db.cursor()
        cur.execute('select id from user where username = "%s";' % data['username'])
        curresult = cur.fetchone()
        if not curresult:
            return "no such user",404 # shouldn't do this because of security issue but whatevs

        password =  md5(data['password'].encode('utf-8')).hexdigest()# {u'username': u'demo', u'password': u'demo'} 
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
    data = json.loads(str(request.data.decode('utf-8')))
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

def access_token_user(access_token): # returns userid of token holder or None if invalid
    cur = g.db.cursor()
    query = 'select id,user_id from auth where access_token = "{}";'.format(access_token)
    cur.execute(query)
    curresult = cur.fetchone()
    if not curresult:
        return None
    else:
        return curresult[1]
    
    
    
@app.route('/tweet/<int:tweet_id>', methods=['GET','DELETE']) 
def tweet(tweet_id=None):    
    if request.method == 'DELETE':
        data = json.loads(str(request.data.decode('utf-8')))
        if 'access_token' not in data:
            return "No access_token!",401
        user = access_token_user(data['access_token'])
        if user is None:
            return "Token invalid",401
        cur = g.db.cursor()
        query = 'select id,user_id,date(created)||"T"||time(created),content from tweet where id={};'.format(tweet_id )
        # print command
        cur.execute(query)
        curresult = cur.fetchone()
        if not curresult:
            return "Tweet-id doesn't exist, ya dingus!",404

        query = 'select id,user_id,date(created)||"T"||time(created),content from tweet where id={} and user_id={};'.format(tweet_id,user )
        # print query
        cur.execute(query)
        curresult = cur.fetchone()
        if not curresult:
            return "Not your tweet, ya dingus!",401
            
        query = 'delete from tweet where id = {} and user_id = {};'.format(tweet_id,user )
        #print query
        cur.execute(query)
        g.db.commit();
            
        return 'Deleted',204
            
    elif request.method =='GET' : # Get method
        #print type(tweet_id)
        cur = g.db.cursor()
        query = 'select id,user_id,date(created)||"T"||time(created),content from tweet where id={};'.format(tweet_id )
        # print command
        cur.execute(query)
        curresult = cur.fetchone()
        if not curresult:
            return "Tweet-id doesn't exist, ya dingus!",404
        # print curresult
        
        tweetinfo =   dict({"id": curresult[0], "content" : curresult[3], "date" : curresult[2] , "profile": "/profile/"+get_username_from_id(curresult[1]), "uri" : '/tweet/'+str(tweet_id) })
        #print tweetinfo
        resp = Response(response=json.dumps(tweetinfo),    status=200,     mimetype="application/json")
        return(resp)
        
    
@app.route('/tweet', methods=['POST']) 
def tweet_noparams(tweet_id=None):
    
    if not request.content_type == 'application/json':
        return "not json",400
     
    data = json.loads(str(request.data.decode('utf-8')))
    if 'access_token' not in data:
        return "No access_token!",401
    user = access_token_user(data['access_token'])
    if user is None:
        return "Token invalid",401
    cur = g.db.cursor()   
    query = "insert into tweet(user_id,content) values ({},'{}');".format(user,data['content'])
    cur.execute(query)
    g.db.commit()
    return 'saved',201


    
def _get_tweet_data(user_id):
    query = 'select id, content, date(created)||"T"||time(created) from tweet where user_id = "{}"  '.format(user_id)
    #tweets = []
    cur = g.db.execute(query)
    #for row in cur.fetchall():
    #    tweets.append( {"id" : row[0], "text" : row[1], "date" : row[2], "profile": get_username_from_id(user_id) , "uri" : '/tweet/'+str(row[0])  }  )
    
    tweets = [ {"id" : row[0], "text" : row[1], "date": row[2],   "uri" : '/tweet/'+str(row[0])} for row in cur.fetchall() ]  
    
    return tweets
    
@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
    if request.method == 'GET':
        cur = g.db.cursor()
        query_user = 'select id, username, first_name, last_name, birth_date from user where username = "{}";'.format(username)
        # print query_user
        cur.execute(query_user)
        result_user = cur.fetchone()
        if not result_user:
            return "No such user!",404
        id_temp = result_user[0]
        tweets = _get_tweet_data(id_temp)
#        del tweets[profile]
#        import ipdb;  ipdb.set_trace()
        profileinfo =    {
            "user_id"  : result_user[0], 
            "username" : str(result_user[1]), 
            "first_name": result_user[2],
            "last_name": result_user[3], 
            "birth_date": result_user[4],
            "tweet": tweets,
            "tweet_count": len ( tweets )
        }  
 
#       
        resp = Response(response=json.dumps( profileinfo ) ,    status=200,      content_type="application/json") 
        #resp.charset='utf-8'
  
        
        #return json.dumps(profileinfo), 200, {'Content-Type': JSON_MIME_TYPE}
        return(resp)
        


    
@app.route('/profile', methods=['POST']) 
def profile_noparams(tweet_id=None):
    if not request.content_type == 'application/json':
        return "not json",400
    data = json.loads(str(request.data.decode('utf-8')))
    if 'access_token' not in data:
        return "No access_token!",401
    user = access_token_user(data['access_token'])
    if user is None:
        return "Token invalid",401
    if (("first_name" not in data) or ("last_name" not in data) or ("birth_date" not in data) ):
        return "Not all elements present",400
 
    cur = g.db.cursor()   
    query = "update user set first_name='{}',last_name='{}',birth_date='{}' where id={};".format(data['first_name'],data['last_name'],data['birth_date'],user)
    cur.execute(query)
    g.db.commit()
    return 'profile saved',201        